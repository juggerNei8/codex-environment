from __future__ import annotations

from typing import Any, Optional

from .config import SimulatorBackendConfig
from .paths import ExportPaths
from .local_cache import read_json, is_fresh
from .http_client import BackendHttpClient


class SimulatorDataClient:
    def __init__(self, cfg: Optional[SimulatorBackendConfig] = None) -> None:
        self.cfg = cfg or SimulatorBackendConfig()
        self.paths = ExportPaths(self.cfg.cache_dir)
        self.http = BackendHttpClient(self.cfg)

    def _load_preferring_file(
        self,
        *,
        json_path: str,
        endpoint_path: str,
        params: Optional[dict] = None,
        empty_default: Any,
    ) -> Any:
        local = read_json(json_path)

        if local is not None and is_fresh(json_path, self.cfg.max_age_seconds):
            return local

        data = self.http.get_data(endpoint_path, params=params)
        if data is not None:
            return data

        if local is not None:
            return local

        return empty_default

    def load_teams(self, competition: Optional[str] = None) -> list[dict]:
        comp = competition or self.cfg.competition
        return self._load_preferring_file(
            json_path=self.paths.teams_json,
            endpoint_path="/api/teams",
            params={"competition": comp},
            empty_default=[],
        )

    def load_fixtures(self, competition: Optional[str] = None) -> list[dict]:
        comp = competition or self.cfg.competition
        return self._load_preferring_file(
            json_path=self.paths.fixtures_json,
            endpoint_path="/api/fixtures",
            params={"competition": comp},
            empty_default=[],
        )

    def load_standings(self, competition: Optional[str] = None) -> list[dict]:
        comp = competition or self.cfg.competition
        return self._load_preferring_file(
            json_path=self.paths.standings_json,
            endpoint_path="/api/standings",
            params={"competition": comp},
            empty_default=[],
        )

    def load_news(self, competition: Optional[str] = None) -> list[dict]:
        comp = competition or self.cfg.competition
        return self._load_preferring_file(
            json_path=self.paths.news_json,
            endpoint_path="/api/news",
            params={"competition": comp},
            empty_default=[],
        )

    def load_logos(self, competition: Optional[str] = None) -> list[dict]:
        comp = competition or self.cfg.competition
        return self._load_preferring_file(
            json_path=self.paths.logos_json,
            endpoint_path="/api/logos",
            params={"competition": comp},
            empty_default=[],
        )

    def load_team_form(self, team: str, competition: Optional[str] = None) -> dict:
        comp = competition or self.cfg.competition
        data = self.http.get_data("/api/team-form", params={"competition": comp, "team": team})
        if data is not None:
            return data

        fixtures = read_json(self.paths.fixtures_json) or []
        return _fallback_compute_form_from_fixtures(fixtures, team=team, competition=comp)

    def load_usage(self) -> dict:
        return self.http.get_data("/api/config/usage") or {}

    def load_export_status(self) -> dict:
        return self.http.get_data("/api/export/status") or {}

    def load_live_games(self) -> dict:
        return self.http.get_data("/api/live-games") or {}

    def load_odds_markets(self) -> dict:
        return self.http.get_data("/api/odds/markets") or {}

    def load_odds_tournaments(self, tournament_ids: str) -> dict:
        return self.http.get_data("/api/odds/tournaments", params={"tournament_ids": tournament_ids}) or {}

    def load_odds_fixture(self, fixture_id: str) -> dict:
        return self.http.get_data("/api/odds/fixture", params={"fixture_id": fixture_id}) or {}

    def load_bet365_prematch(self) -> dict:
        return self.http.get_data("/api/odds/bet365-prematch") or {}


def _fallback_compute_form_from_fixtures(fixtures: list[dict], *, team: str, competition: str) -> dict:
    finished = []
    for m in fixtures or []:
        if m.get("status") != "FINISHED":
            continue
        if team not in (m.get("home"), m.get("away")):
            continue
        if "homeGoals" not in m or "awayGoals" not in m:
            continue
        finished.append(m)

    finished.sort(key=lambda x: x.get("utcDate") or "", reverse=True)

    sequence = []
    wins_recent = draws_recent = losses_recent = 0
    gf_total = ga_total = 0

    for m in finished[:10]:
        home = m.get("home")
        hg = int(m.get("homeGoals"))
        ag = int(m.get("awayGoals"))

        if team == home:
            gf, ga = hg, ag
        else:
            gf, ga = ag, hg

        gf_total += gf
        ga_total += ga

        if gf > ga:
            sequence.append("W")
            wins_recent += 1
        elif gf == ga:
            sequence.append("D")
            draws_recent += 1
        else:
            sequence.append("L")
            losses_recent += 1

    return {
        "competition": competition,
        "team": team,
        "form_last5": sequence[:5],
        "sequence": sequence,
        "goals_for_recent": gf_total,
        "goals_against_recent": ga_total,
        "wins_recent": wins_recent,
        "draws_recent": draws_recent,
        "losses_recent": losses_recent,
        "injuries_count": 0,
        "cards_pressure": 0.0,
        "morale": 0.5,
        "offline": True,
    }