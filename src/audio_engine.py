from __future__ import annotations

import os
from pathlib import Path

try:
    import winsound
except Exception:
    winsound = None


class AudioEngine:
    def __init__(self):
        self.crowd_playing = False
        self.muted = False
        self.sound_dir = self._resolve_sound_dir()

    def _resolve_sound_dir(self) -> Path:
        cache_dir = os.getenv("CACHE_DIR", "").strip()
        if cache_dir:
            candidate = Path(cache_dir) / "assets" / "sounds"
            if candidate.exists():
                return candidate
        project_root = Path(__file__).resolve().parent
        return project_root / "assets" / "sounds"

    def _sound_path(self, stem: str):
        for ext in (".wav", ".WAV"):
            candidate = self.sound_dir / f"{stem}{ext}"
            if candidate.exists():
                return candidate
        return None

    def _play_async(self, path: Path | None, loop: bool = False):
        if self.muted:
            return
        if winsound is None or path is None:
            return
        flags = winsound.SND_FILENAME | winsound.SND_ASYNC
        if loop:
            flags |= winsound.SND_LOOP
        try:
            winsound.PlaySound(str(path), flags)
        except Exception:
            pass

    def set_muted(self, muted: bool):
        self.muted = muted
        if muted:
            self.stop_crowd()

    def play_crowd(self):
        if self.muted or self.crowd_playing:
            return
        self._play_async(self._sound_path("crowd"), loop=True)
        self.crowd_playing = True

    def stop_crowd(self):
        self.crowd_playing = False
        if winsound is not None:
            try:
                winsound.PlaySound(None, winsound.SND_PURGE)
            except Exception:
                pass

    def play_goal(self):
        if self.muted:
            return
        self._play_async(self._sound_path("goal"), loop=False)

    def play_whistle(self):
        if self.muted:
            return
        self._play_async(self._sound_path("whistle"), loop=False)
