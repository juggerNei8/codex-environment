import os
from pathlib import Path
import tkinter as tk


class LogoLoader:
    def __init__(self):
        self.cache = {}

    def _slug(self, team_name: str) -> str:
        slug = "".join(c.lower() if c.isalnum() else "_" for c in team_name)
        while "__" in slug:
            slug = slug.replace("__", "_")
        return slug.strip("_")

    def _alt_names(self, team_name: str):
        base = team_name.strip()
        names = {base}

        replacements = [
            (" FC", ""),
            (" CF", ""),
            (" AFC", ""),
            (" SC", ""),
            (" AC", ""),
            (" Calcio", ""),
            (" Club", ""),
        ]

        for old, new in replacements:
            if base.endswith(old):
                names.add(base.replace(old, new).strip())

        if "United" in base:
            names.add(base.replace("United", "Utd"))
        if "Utd" in base:
            names.add(base.replace("Utd", "United"))
        if "Inter Milan" in base:
            names.add("Inter")
        if "Paris Saint-Germain" in base:
            names.add("PSG")

        return sorted(names)

    def _candidate_paths(self, team_name: str):
        candidates = []
        cache_dir = os.getenv("CACHE_DIR", "").strip()

        roots = []
        if cache_dir:
            roots.append(Path(cache_dir) / "assets" / "logos")

        project_root = Path(__file__).resolve().parent.parent
        roots.append(project_root / "assets" / "logos")

        exts = [".png", ".gif", ".ppm", ".pgm", ".jpg", ".jpeg"]

        for root in roots:
            for alt in self._alt_names(team_name):
                slug = self._slug(alt)
                for ext in exts:
                    candidates.append(root / f"{slug}{ext}")

        return candidates

    def _load_photo(self, path: Path, size: str):
        img = tk.PhotoImage(file=str(path))
        w = max(1, img.width())
        h = max(1, img.height())

        target_px = {
            "tiny": 20,
            "small": 28,
            "medium": 40,
        }.get(size, 28)

        sx = max(1, w // target_px)
        sy = max(1, h // target_px)

        return img.subsample(sx, sy)

    def load(self, team: str, small: bool = False):
        size = "small" if small else "medium"
        return self.load_size(team, size=size)

    def load_size(self, team: str, size: str = "small"):
        key = (team, size)
        if key in self.cache:
            return self.cache[key]

        for path in self._candidate_paths(team):
            if path.exists():
                try:
                    img = self._load_photo(path, size)
                    self.cache[key] = img
                    return img
                except Exception:
                    continue

        return None