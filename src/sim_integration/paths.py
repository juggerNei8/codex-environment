from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class ExportPaths:
    cache_dir: str

    @property
    def teams_json(self) -> str:
        return os.path.join(self.cache_dir, "teams.json")

    @property
    def fixtures_json(self) -> str:
        return os.path.join(self.cache_dir, "fixtures.json")

    @property
    def standings_json(self) -> str:
        return os.path.join(self.cache_dir, "standings.json")

    @property
    def news_json(self) -> str:
        return os.path.join(self.cache_dir, "news.json")

    @property
    def logos_json(self) -> str:
        return os.path.join(self.cache_dir, "logos.json")

    @property
    def logos_assets_dir(self) -> str:
        return os.path.join(self.cache_dir, "assets", "logos")

    def logo_asset_path(self, team_slug: str) -> str:
        return os.path.join(self.logos_assets_dir, f"{team_slug}.png")