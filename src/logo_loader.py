import os
from pathlib import Path
import tkinter as tk


class LogoLoader:
    def __init__(self):
        self.cache = {}

    def _candidate_paths(self, team_name: str):
        safe = "".join(c.lower() if c.isalnum() else "_" for c in team_name).strip("_")

        candidates = []

        # backend cache logos
        cache_dir = os.getenv("CACHE_DIR", "")
        if cache_dir:
            candidates.append(Path(cache_dir) / "assets" / "logos" / f"{safe}.png")

        # local project assets fallback
        project_root = Path(__file__).resolve().parent.parent
        candidates.append(project_root / "assets" / "logos" / f"{safe}.png")

        return candidates

    def load(self, team: str, small: bool = False):
        key = (team, small)
        if key in self.cache:
            return self.cache[key]

        for path in self._candidate_paths(team):
            if path.exists():
                try:
                    img = tk.PhotoImage(file=str(path))
                    if small:
                        img = img.subsample(max(1, img.width() // 36), max(1, img.height() // 36))
                    else:
                        img = img.subsample(max(1, img.width() // 64), max(1, img.height() // 64))
                    self.cache[key] = img
                    return img
                except Exception:
                    continue

        return None