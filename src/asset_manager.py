import os
import tkinter as tk


class AssetManager:
    def __init__(self):
        self.cache = {}

    def project_root(self):
        here = os.path.dirname(os.path.abspath(__file__))
        return os.path.normpath(os.path.join(here, ".."))

    def _safe_key(self, path):
        return path.replace("\\", "/").lower()

    def load_photo(self, path):
        key = self._safe_key(path)
        if key in self.cache:
            return self.cache[key]

        if not os.path.exists(path):
            return None

        try:
            img = tk.PhotoImage(file=path)
            self.cache[key] = img
            return img
        except Exception:
            return None

    def load_pitch_image(self):
        base = os.path.join(self.project_root(), "assets", "pitch")
        for name in ("pitch.png", "Pitch 1.png", "football_pitch.png"):
            img = self.load_photo(os.path.join(base, name))
            if img is not None:
                return img
        return None

    def load_ball_image(self):
        base = os.path.join(self.project_root(), "assets", "balls")
        for name in ("ball.png", "SoccerBall.png", "soccer_ball.png"):
            img = self.load_photo(os.path.join(base, name))
            if img is not None:
                return img
        return None