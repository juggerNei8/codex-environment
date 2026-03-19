from __future__ import annotations

import json
import os
import urllib.request
from pathlib import Path
import tkinter as tk


class LogoLoader:
    def __init__(self):
        self.cache = {}
        self._url_index = None

    def _slug(self, team_name: str) -> str:
        slug = "".join(c.lower() if c.isalnum() else "_" for c in (team_name or ""))
        while "__" in slug:
            slug = slug.replace("__", "_")
        return slug.strip("_")

    def _alt_names(self, team_name: str):
        base = (team_name or "").strip()
        names = {base}
        replacements = [(" FC", ""), (" CF", ""), (" AFC", ""), (" SC", ""), (" AC", ""), (" Calcio", ""), (" Club", "")]
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
        return sorted(n for n in names if n)

    def _logo_roots(self):
        roots = []
        cache_dir = os.getenv("CACHE_DIR", "").strip()
        if cache_dir:
            roots.append(Path(cache_dir) / "assets" / "logos")
            default_comp = os.getenv("DEFAULT_COMPETITION", "PL").strip().upper()
            roots.append(Path(cache_dir) / default_comp / "assets" / "logos")
        project_root = Path(__file__).resolve().parent
        roots.append(project_root / "assets" / "logos")
        return roots

    def _candidate_paths(self, team_name: str):
        candidates = []
        exts = [".png", ".gif", ".ppm", ".pgm"]
        for root in self._logo_roots():
            for alt in self._alt_names(team_name):
                slug = self._slug(alt)
                for ext in exts:
                    candidates.append(root / f"{slug}{ext}")
        return candidates

    def _load_photo(self, path: Path, size: str):
        img = tk.PhotoImage(file=str(path))
        w = max(1, img.width())
        h = max(1, img.height())
        target_px = {"tiny": 20, "small": 28, "medium": 40}.get(size, 28)
        sx = max(1, w // target_px)
        sy = max(1, h // target_px)
        return img.subsample(sx, sy)

    def _build_url_index(self):
        index = {}
        cache_dir = os.getenv("CACHE_DIR", "").strip()
        if not cache_dir:
            return index
        candidates = [
            Path(cache_dir) / "logos.json",
            Path(cache_dir) / os.getenv("DEFAULT_COMPETITION", "PL").strip().upper() / "logos.json",
        ]
        for file_path in candidates:
            if not file_path.exists():
                continue
            try:
                payload = json.loads(file_path.read_text(encoding="utf-8"))
            except Exception:
                continue
            entries = payload if isinstance(payload, list) else payload.get("items", [])
            if not isinstance(entries, list):
                continue
            for item in entries:
                if not isinstance(item, dict):
                    continue
                team_name = item.get("team") or item.get("name") or item.get("teamName")
                url = item.get("logo") or item.get("logo_url") or item.get("badge") or item.get("badge_url") or item.get("crest")
                if team_name and url:
                    index[self._slug(team_name)] = url
        return index

    def _download_logo_if_possible(self, team_name: str):
        if self._url_index is None:
            self._url_index = self._build_url_index()
        slug = self._slug(team_name)
        url = self._url_index.get(slug)
        if not url:
            for alt in self._alt_names(team_name):
                url = self._url_index.get(self._slug(alt))
                if url:
                    break
        if not url:
            return None
        roots = self._logo_roots()
        if not roots:
            return None
        target_dir = roots[0]
        try:
            target_dir.mkdir(parents=True, exist_ok=True)
        except Exception:
            return None
        target = target_dir / f"{slug}.png"
        if target.exists():
            return target
        try:
            urllib.request.urlretrieve(url, target)
            if target.exists():
                return target
        except Exception:
            return None
        return None

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
        downloaded = self._download_logo_if_possible(team)
        if downloaded and downloaded.exists():
            try:
                img = self._load_photo(downloaded, size)
                self.cache[key] = img
                return img
            except Exception:
                pass
        return None

    def short_text_fallback(self, team: str) -> str:
        words = [w for w in (team or "").split() if w]
        if not words:
            return "?"
        if len(words) == 1:
            return words[0][:3].upper()
        return "".join(w[0] for w in words[:3]).upper()
