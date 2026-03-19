from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class ExportPaths:
    cache_dir: str

    def _competition_dir(self, competition: str) -> str:
        comp = (competition or "PL").strip().upper()
        return os.path.join(self.cache_dir, comp)

    def _legacy_path(self, filename: str) -> str:
        return os.path.join(self.cache_dir, filename)

    def teams_json_for(self, competition: str) -> str:
        return os.path.join(self._competition_dir(competition), "teams.json")

    def fixtures_json_for(self, competition: str) -> str:
        return os.path.join(self._competition_dir(competition), "fixtures.json")

    def standings_json_for(self, competition: str) -> str:
        return os.path.join(self._competition_dir(competition), "standings.json")

    def news_json_for(self, competition: str) -> str:
        return os.path.join(self._competition_dir(competition), "news.json")

    def logos_json_for(self, competition: str) -> str:
        return os.path.join(self._competition_dir(competition), "logos.json")

    def logos_assets_dir_for(self, competition: str) -> str:
        return os.path.join(self._competition_dir(competition), "assets", "logos")

    def sounds_assets_dir(self) -> str:
        return os.path.join(self.cache_dir, "assets", "sounds")

    def logo_asset_path(self, team_slug: str, competition: str) -> str:
        return os.path.join(self.logos_assets_dir_for(competition), f"{team_slug}.png")

    @property
    def teams_json(self) -> str:
        return self._legacy_path("teams.json")

    @property
    def fixtures_json(self) -> str:
        return self._legacy_path("fixtures.json")

    @property
    def standings_json(self) -> str:
        return self._legacy_path("standings.json")

    @property
    def news_json(self) -> str:
        return self._legacy_path("news.json")

    @property
    def logos_json(self) -> str:
        return self._legacy_path("logos.json")

    @property
    def logos_assets_dir(self) -> str:
        return os.path.join(self.cache_dir, "assets", "logos")
