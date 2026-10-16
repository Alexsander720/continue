"""Standalone Deck adapter; shared PC media safeguards, Deck budgets/presets."""
import time
import standalone_media as base
from public_media_policy import PCMediaManager


class DeckMediaManager(PCMediaManager):
    def get_preset(self,preset):
        return dict(base.PRESETS.get(str(preset),base.PRESETS['light']))

    def _configure(self,settings):
        base.MediaManager._configure(self,settings)

    def enforce_limit(self,limit_gb):
        return base.MediaManager.enforce_limit(self,limit_gb if limit_gb in (1,2,4,8) else 2)

    def prepare_music(self,appid,name,settings,*,force=False):
        with self.music_lock:
            self._operation_deadline=time.monotonic()+240
            try:
                self._configure(settings)
                self.enforce_limit(settings.get('disk_limit_gb',2))
                return self._maybe_theme(appid,name,settings,force=force) or {'ok':True,'cached':True}
            finally:
                self.active=None
                self._operation_deadline=None

    def build(self,appid,name,settings,source=None,*,force=False):
        # Deck's original media policy owns video presets/AC gating. Music is a
        # separate lightweight operation and must not inherit the AC-only gate.
        with self.music_lock:
            self._operation_deadline=time.monotonic()+600
            try:
                return base.MediaManager.build(self,appid,name,dict(settings,theme_music_consent=False),source,force=force)
            finally:
                self._operation_deadline=None
