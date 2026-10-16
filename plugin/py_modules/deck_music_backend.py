"""Export-only standalone Deck music endpoints; no owner-mode side effects."""
import asyncio
import math
import re
import secrets
import threading
from pathlib import Path


def app_id(value):
    return type(value) is int and 1<=value<=0xffffffff


def with_music(Base,data):
    class DeckMusicPlugin(Base):
        async def get_settings(self):
            result=await super().get_settings()
            if self._is_standalone():
                volume=result.get('music_volume',.4)
                result['music_volume']=volume if type(volume) in (int,float) and math.isfinite(volume) and 0<=volume<=1 else .4
                if not isinstance(result.get('music_choices'),dict):result['music_choices']={}
            return result

        async def set_setting(self,key,value):
            if self._is_standalone() and key=='music_volume':
                if type(value) in (int,float) and math.isfinite(value) and 0<=value<=1:
                    settings=await self.get_settings();settings[key]=value;self._write_settings(settings)
                return await self.get_settings()
            if self._is_standalone() and key=='theme_music_consent' and value is False:
                # Invalidate queued and active setup before any awaited settings I/O.
                self._music_consent_epoch=getattr(self,'_music_consent_epoch',0)+1
                manager=getattr(self,'_standalone_media',None)
                if manager:manager.cancel()
            result=await super().set_setting(key,value)
            return result

        def _music_allowed(self):
            if not self._is_standalone() or getattr(self,'_music_closed',False) or getattr(self,'_media_game_running',False):return False
            try:
                power=self._power_sync()
                battery=power.get('battery')
                if not power.get('ac') and type(battery) in (int,float) and battery<=15:return False
                return not self._running_game()
            except Exception:return False

        def _music_setup_power_allowed(self):
            try:
                power=self._power_sync();battery=power.get('battery')
                return bool(power.get('ac') or (type(battery) in (int,float) and math.isfinite(battery) and battery>30))
            except Exception:return False

        def _music_setup_allowed(self):
            return self._music_setup_power_allowed() and self._music_allowed()

        def _media(self):
            if not self._is_standalone():return super()._media()
            manager=getattr(self,'_standalone_media',None)
            if manager is None:
                from deck_music_media import DeckMediaManager
                from deck_media_runtime import MediaRuntime
                manager=DeckMediaManager(data,self._plugin_dir(),allowed=self._deck_work_allowed)
                manager.runtime=MediaRuntime(data,Path(self._plugin_dir())/'assets/deck_media_runtime.json',allowed=lambda:self._music_setup_allowed() if getattr(self,'_runtime_setup',False) else self._music_allowed())
                self._standalone_media=manager
            return manager

        def _deck_work_allowed(self):
            if getattr(self,'_runtime_setup',False):return self._music_setup_allowed()
            return self._music_allowed() if getattr(self,'_music_operation',False) else self._media_work_allowed()

        def _music_job(self,key,work):
            jobs=getattr(self,'_music_jobs',{})
            for job,(existing,task) in jobs.items():
                if key==existing and not task.done():return {'ok':True,'pending':True,'job':job}
            if any(not task.done() for _,task in jobs.values()):return {'ok':False,'deferred':'busy'}
            async def guarded():
                async with self._media_lock():
                    if key[0]=='setup' and not self._music_setup_power_allowed():return {'ok':False,'deferred':'charging_required'}
                    if not self._music_allowed():return {'ok':False,'deferred':'game_or_low_battery'}
                    self._music_operation=True
                    try:return await work()
                    except asyncio.CancelledError:raise
                    except Exception:return {'ok':False,'error':'media_preparation_failed'}
                    finally:self._music_operation=False
            job=secrets.token_hex(12);jobs[job]=(key,asyncio.create_task(guarded()))
            while len(jobs)>24:
                old=next((j for j,(_,t) in jobs.items() if t.done()),None)
                if old is None:break
                jobs.pop(old)
            self._music_jobs=jobs
            return {'ok':True,'pending':True,'job':job}

        async def music_job_status(self,job):
            if not isinstance(job,str) or not re.fullmatch('[a-f0-9]{24}',job):return {'done':True,'result':{'ok':False,'error':'invalid_job'}}
            row=getattr(self,'_music_jobs',{}).get(job)
            if not row:return {'done':True,'result':{'ok':False,'error':'unknown_job'}}
            if not row[1].done():return {'done':False}
            try:return {'done':True,'result':row[1].result()}
            except (Exception,asyncio.CancelledError):return {'done':True,'result':{'ok':False,'error':'cancelled'}}

        async def setup_deck_music(self,consent=False,force=False):
            if not self._is_standalone():return {'ok':False,'standalone':False}
            if consent is not True or type(force) is not bool:return {'ok':False,'consent_required':True}
            epoch=getattr(self,'_music_consent_epoch',0)
            async def prepare():
                def cancelled():
                    return epoch!=getattr(self,'_music_consent_epoch',0) or getattr(manager,'_cancelled',False)
                if epoch!=getattr(self,'_music_consent_epoch',0):return {'ok':False,'error':'cancelled'}
                previous=getattr(self,'_standalone_media',None)
                if previous and getattr(previous,'_cancelled',False):self._standalone_media=None
                manager=self._media();loop=asyncio.get_running_loop()
                self._runtime_setup=True
                try:ready=await loop.run_in_executor(None,lambda:manager.runtime.prepare(consent=True))
                finally:self._runtime_setup=False
                if cancelled():return {'ok':False,'error':'cancelled'}
                if not ready.get('ok'):return ready
                installed=await loop.run_in_executor(None,lambda:manager.install_ytdlp(True,force))
                if cancelled():return {'ok':False,'error':'cancelled'}
                if installed.get('ok'):
                    settings=await self.get_settings()
                    if cancelled():return {'ok':False,'error':'cancelled'}
                    settings.update(theme_music_consent=True,hub_music=True,home_music=True)
                    self._write_settings(settings)
                return installed
            return self._music_job(('setup',force),prepare)

        async def refresh_music(self,appid,name='',force=False):
            if not self._is_standalone():return {'ok':False,'standalone':False}
            if not app_id(appid) or type(force) is not bool:return {'ok':False,'error':'invalid_request'}
            settings=await self.get_settings()
            if (settings.get('music_choices') or {}).get(str(appid))=='none':return {'ok':True,'disabled':True}
            if not settings.get('theme_music_consent'):return {'ok':False,'consent_required':True}
            if not(settings.get('home_music') or settings.get('hub_music')):return {'ok':True,'disabled':True}
            if not self._music_allowed():return {'ok':False,'deferred':'game_or_low_battery'}
            async def prepare():
                # Read settings again when queued work really begins; a revoked
                # consent or per-game None must win over the earlier request.
                current=await self.get_settings()
                return await asyncio.get_running_loop().run_in_executor(None,lambda:self._media().prepare_music(appid,str(name)[:300],current,force=force))
            return self._music_job(('theme',appid,force),prepare)

        async def set_music_choice(self,appid,choice):
            if not self._is_standalone() or not app_id(appid) or choice not in ('auto','none'):return {'ok':False,'error':'invalid_choice'}
            settings=await self.get_settings();choices=dict(settings.get('music_choices') or {})
            if choice=='auto':choices.pop(str(appid),None)
            else:choices[str(appid)]=choice
            if len(choices)>10000:return {'ok':False,'error':'too_many_choices'}
            settings['music_choices']=choices;self._write_settings(settings)
            manager=getattr(self,'_standalone_media',None)
            if manager:manager.invalidate_theme(appid)
            return {'ok':True,'settings':settings}

        async def get_music_files(self):
            if not self._is_standalone():return await super().get_music_files()
            settings=await self.get_settings()
            return await asyncio.get_running_loop().run_in_executor(None,lambda:self._media().music_files(settings))

        async def get_deck_music_status(self,appid=None):
            if not self._is_standalone():return {'standalone':False}
            settings=await self.get_settings();manager=self._media()
            def snapshot():
                state=manager._state();files=manager.music_files(settings)
                attempt=(state.get('theme_attempts') or {}).get(str(appid)) or {}
                choice=(settings.get('music_choices') or {}).get(str(appid),'auto')
                status=('setup_required' if not settings.get('theme_music_consent') else 'disabled' if choice=='none' or not(settings.get('hub_music') or settings.get('home_music')) else 'ready' if str(appid) in files else 'error' if attempt.get('ok') is False else 'waiting')
                from standalone_media import THEME_REASONS
                if status == 'error' and attempt.get('reason') in THEME_REASONS | {'youtube_blocked','python3_required'}:status = attempt['reason']
                active=any(not t.done() for _,t in getattr(self,'_music_jobs',{}).values())
                return {'state':'preparing' if active else status,'file':files.get(str(appid)),
                    'runtime':manager.runtime.status(),'loader':{k:v for k,v in (state.get('yt_dlp') or {}).items() if k in ('version','checked_at')},
                    'reason':attempt.get('reason') if not active and status != 'ready' else None,
                    'error':status if status in THEME_REASONS | {'youtube_blocked','python3_required'} else 'download_failed' if status=='error' else None,'choice':choice,
                    'rollback_available':bool(state.get('yt_dlp_previous'))}
            return await asyncio.get_running_loop().run_in_executor(None,snapshot)

        async def update_music_loader(self,consent=False,rollback=False):
            if not self._is_standalone() or consent is not True or type(rollback) is not bool:return {'ok':False,'consent_required':True}
            async def update():
                m=self._media()
                method=(lambda:m.rollback_ytdlp(True)) if rollback else (lambda:m.install_ytdlp(True,True))
                return await asyncio.get_running_loop().run_in_executor(None,method)
            return self._music_job(('loader',rollback),update)

        async def _unload(self):
            self._music_closed=True
            await super()._unload()
            tasks=[t for _,t in getattr(self,'_music_jobs',{}).values() if not t.done()]
            for task in tasks:task.cancel()
            if tasks:await asyncio.gather(*tasks,return_exceptions=True)
    return DeckMusicPlugin
