"""Hash-verified yt-dlp updates with durable rollback; no execution on recovery."""
import copy
import os
from pathlib import Path
import re
import shutil
import stat
import threading

NAMES=('yt-dlp','yt-dlp.previous','yt-dlp.download.part','yt-dlp.transaction.old','yt-dlp.transaction.json')


def safe(m):
    root=Path(os.path.abspath(m.data))
    for p in [m.state_path,*[m.bin/n for n in NAMES]]:
        p=Path(os.path.abspath(p));p.relative_to(root)
        for parent in (p,*p.parents):
            if parent.exists() or parent.is_symlink():
                attrs=parent.lstat()
                if stat.S_ISLNK(attrs.st_mode) or getattr(attrs,'st_file_attributes',0)&0x400:raise ValueError('unsafe loader path')
            if parent==root:break


def valid(m,path,meta):
    digest=meta.get('sha256') if isinstance(meta,dict) else None
    return bool(re.fullmatch('[a-f0-9]{64}',str(digest)) and path.is_file() and path.stat().st_size>=512*1024 and m._hash_file(path)==digest)


def put_state(m,state):
    m._atomic_json(m.state_path,state)


def recover(m):
    if not hasattr(m,'_loader_update_lock'):m._loader_update_lock=threading.RLock()
    with m._loader_update_lock:
        return _recover_unlocked(m)


def _recover_unlocked(m):
    if getattr(m,'_loader_recovering',False):return
    m._loader_recovering=True
    try:
        safe(m);journal=m.bin/'yt-dlp.transaction.json'
        if not journal.exists():return
        import json
        if journal.stat().st_size>65536:raise ValueError('invalid loader recovery')
        j=json.loads(journal.read_text(encoding='utf-8'))
        if j.get('schema')!=1 or not isinstance(j.get('old'),dict) or not isinstance(j.get('new'),dict):raise ValueError('invalid loader recovery')
        current=m.bin/'yt-dlp';old=m.bin/'yt-dlp.transaction.old';state=m._state()
        committed=(state.get('yt_dlp') or {}).get('sha256')==j['new'].get('sha256') and valid(m,current,j['new'])
        if committed:
            if j.get('had_old'):
                if not valid(m,old,j['old']):raise ValueError('invalid old loader recovery')
                os.replace(old,m.bin/'yt-dlp.previous')
                state['yt_dlp_previous']=j['old'];put_state(m,state)
        else:
            if j.get('had_old'):
                if not valid(m,old,j['old']):raise ValueError('invalid old loader recovery')
                os.replace(old,current)
            elif valid(m,current,j['new']):current.unlink()
            state['yt_dlp']=j['old'];put_state(m,state)
        journal.unlink();old.unlink(missing_ok=True)
    finally:m._loader_recovering=False


def commit(m,candidate,new_meta):
    safe(m);recover(m)
    state=m._state();old_meta=copy.deepcopy(state.get('yt_dlp') or {})
    current=m.bin/'yt-dlp';old=m.bin/'yt-dlp.transaction.old';journal=m.bin/'yt-dlp.transaction.json'
    had_old=valid(m,current,old_meta)
    if had_old:
        with current.open('rb') as source,old.open('wb') as output:
            shutil.copyfileobj(source,output);output.flush();os.fsync(output.fileno())
    m._atomic_json(journal,{'schema':1,'old':old_meta,'new':new_meta,'had_old':had_old})
    try:
        m._promote(candidate,current)
        state=m._state();state['yt_dlp']=new_meta;put_state(m,state)
        recover(m)
    except Exception:
        recover(m)
        raise


def update(m,consent=False,force=False):
    if consent is not True:return {'ok':False,'consent_required':True}
    if not hasattr(m,'_loader_update_lock'):m._loader_update_lock=threading.RLock()
    with m._loader_update_lock:
        old=None;part=m.bin/'yt-dlp.download.part'
        try:
            safe(m);recover(m)
            state=m._state();previous=copy.deepcopy(state.get('yt_dlp') or {})
            current=m.bin/'yt-dlp';old=current if valid(m,current,previous) else None
            checked=previous.get('checked_at')
            retry=900 if previous.get('error') else 7*86400
            if checked is not None and m.now()-float(checked)<retry and not force:
                return {'ok':bool(old),'updated':False,'status':'ready' if old else 'error','retry_at':float(checked)+retry,'error':previous.get('error')}
            state['yt_dlp']={**previous,'checked_at':m.now()};put_state(m,state)
            m._checkpoint();m._check_space(0)
            release=m._json_url('https://api.github.com/repos/yt-dlp/yt-dlp/releases/latest')
            version=str(release.get('tag_name') or '')
            if not re.fullmatch(r'[A-Za-z0-9._-]{1,100}',version):raise ValueError('invalid official loader release')
            assets={a.get('name'):a.get('browser_download_url') for a in release.get('assets') or []}
            for name in ('yt-dlp','SHA2-256SUMS'):
                if assets.get(name)!=f'https://github.com/yt-dlp/yt-dlp/releases/download/{version}/{name}':raise ValueError('loader source is not official')
            sums=m._bytes(assets['SHA2-256SUMS'],limit=4*1024*1024).decode('utf-8','replace')
            match=re.search(r'(?mi)^([0-9a-f]{64})\s+\*?yt-dlp\s*$',sums)
            if not match:raise ValueError('official loader sha256 missing')
            m._stream(assets['yt-dlp'],part,timeout=120,limit=32*1024*1024)
            digest=m._hash_file(part)
            if digest!=match[1].lower():raise ValueError('yt-dlp sha256 mismatch')
            if part.stat().st_size<512*1024:raise ValueError('official loader too small')
            part.chmod(0o700)
            m._checkpoint()
            meta={'version':version,'sha256':digest,'checked_at':m.now()}
            commit(m,part,meta)
            return {'ok':True,'updated':True,'status':'updated',**meta}
        except Exception as exc:
            if getattr(m, '_cancelled', False):
                recover(m)
                return {'ok': False, 'updated': False, 'status': 'cancelled', 'error': 'cancelled'}
            # Errors include only a bounded class/category; paths are never exposed.
            error=str(exc) if isinstance(exc,(ValueError,RuntimeError)) else type(exc).__name__
            try:
                recover(m);state=m._state();meta=state.get('yt_dlp') or {}
                usable=valid(m,m.bin/'yt-dlp',meta)
                state['yt_dlp']={**meta,'checked_at':m.now(),'error':error};put_state(m,state)
            except Exception:usable=bool(old and old.is_file() and valid(m,old,previous)) if 'previous' in locals() else False
            return {'ok':usable,'updated':False,'status':'usable_old' if usable else 'error','error':error,'retry_at':m.now()+900}
        finally:
            try:
                safe(m);part.unlink(missing_ok=True)
            except (OSError,ValueError):pass


def rollback(m,consent=False):
    if consent is not True:return {'ok':False,'consent_required':True}
    if not hasattr(m,'_loader_update_lock'):m._loader_update_lock=threading.RLock()
    with m._loader_update_lock:
        try:
            safe(m);recover(m);state=m._state();meta=dict(state.get('yt_dlp_previous') or {})
            previous=m.bin/'yt-dlp.previous'
            if not valid(m,previous,meta):raise ValueError('previous loader unavailable or sha256 mismatch')
            part=m.bin/'yt-dlp.download.part';shutil.copyfile(previous,part);meta['checked_at']=m.now()
            commit(m,part,meta)
            return {'ok':True,'updated':False,'rolled_back':True,'status':'rolled_back',**meta}
        except Exception as exc:
            return {'ok':False,'updated':False,'rolled_back':False,'error':str(exc) if isinstance(exc,ValueError) else type(exc).__name__}
