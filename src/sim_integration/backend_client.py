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

    def _unwrap_data_list(self, payload: Any) -> list[dict]:
        if isinstance(payload, list):
            return payload
        if isinstance(payload, dict):
            data = payload.get("data")
            if isinstance(data, list):
                return data
            if isinstance(data, dict):
                items = data.get("items")
                if isinstance(items, list):
                    return items
        return []

    def _unwrap_data_dict(self, payload: Any) -> dict:
        if isinstance(payload, dict):
            data = payload.get("data")
            if isinstance(data, dict):
                return data
            return payload
        return {}

    def _filter_competition_rows(self, rows: list[dict], competition: str) -> list[dict]:
        target = (competition or "").strip().upper()
        if not target:
            return [r for r in rows if isinstance(r, dict)]
        filtered = []
        for row in rows or []:
            if not isinstance(row, dict):
                continue
            league = str(row.get("league", "")).strip().upper()
            if not league or league == target:
                filtered.append(row)
        return filtered

    def _load_preferring_file(
        self,
        *,
        json_path: str,
        endpoint_path: str,
        params: Optional[dict] = None,
        empty_default: Any,
        competition: Optional[str] = None,
        expect_list: bool = False,
    ) -> Any:
        local = read_json(json_path)
        comp = (competition or "").strip().upper()

        if local is not None and is_fresh(json_path, self.cfg.max_age_seconds):
            if expect_list:
                rows = self._unwrap_data_list(local)
                filtered = self._filter_competition_rows(rows, comp)
                if filtered:
                    return filtered
            else:
                return local

        data = self.http.get_data(endpoint_path, params=params)
        if data is not None:
            if expect_list:
                rows = self._unwrap_data_list(data)
                filtered = self._filter_competition_rows(rows, comp)
                if filtered:
                    return filtered
                if rows:
                    return rows
            else:
                return data

        if local is not None:
            if expect_list:
                rows = self._unwrap_data_list(local)
                filtered = self._filter_competition_rows(rows, comp)
                return filtered or rows
            return local

        return empty_default

    def load_teams(self, competition: Optional[str] = None) -> list[dict]:
        comp = competition or self.cfg.competition
        return self._load_preferring_file(
            json_path=self.paths.teams_json,
            endpoint_path="/api/teams",
            params={"competition": comp},
            empty_default=[],
            competition=comp,
            expect_list=True,
        )

    def load_fixtures(self, competition: Optional[str] = None) -> list[dict]:
        comp = competition or self.cfg.competition
        return self._load_preferring_file(
            json_path=self.paths.fixtures_json,
            endpoint_path="/api/fixtures",
            params={"competition": comp},
            empty_default=[],
            competition=comp,
            expect_list=True,
        )

    def load_standings(self, competition: Optional[str] = None) -> list[dict]:
        comp = competition or self.cfg.competition
        return self._load_preferring_file(
            json_path=self.paths.standings_json,
            endpoint_path="/api/standings",
            params={"competition": comp},
            empty_default=[],
            competition=comp,
            expect_list=True,
        )

    def load_news(self, competition: Optional[str] = None) -> list[dict]:
        comp = competition or self.cfg.competition
        return self._load_preferring_file(
            json_path=self.paths.news_json,
            endpoint_path="/api/news",
            params={"competition": comp},
            empty_default=[],
            competition=comp,
            expect_list=True,
        )

    def load_logos(self, competition: Optional[str] = None) -> list[dict]:
        comp = competition or self.cfg.competition
        return self._load_preferring_file(
            json_path=self.paths.logos_json,
            endpoint_path="/api/logos",
            params={"competition": comp},
            empty_default=[],
            competition=comp,
            expect_list=True,
        )

    def load_team_form(self, team: str, competition: Optional[str] = None) -> dict:
        comp = competition or self.cfg.competition
        data = self._unwrap_data_dict(
            self.http.get_data("/api/team-form", params={"competition": comp, "team": team})
        )
        if data:
            return data
        fixtures = self.load_fixtures(comp)
        return _fallback_compute_form_from_fixtures(fixtures, team=team, competition=comp)

    def load_usage(self) -> dict:
        return self._unwrap_data_dict(self.http.get_data("/api/config/usage"))

    def load_export_status(self) -> dict:
        return self._unwrap_data_dict(self.http.get_data("/api/export/status"))

    def load_live_games(self) -> dict:
        return self._unwrap_data_dict(self.http.get_data("/api/live-games"))

    def load_odds_markets(self) -> dict:
        return self._unwrap_data_dict(self.http.get_data("/api/odds/markets"))

    def load_odds_tournaments(self, tournament_ids: str) -> dict:
        return self._unwrap_data_dict(
            self.http.get_data("/api/odds/tournaments", params={"tournament_ids": tournament_ids})
        )

    def load_odds_fixture(self, fixture_id: str) -> dict:
        return self._unwrap_data_dict(
            self.http.get_data("/api/odds/fixture", params={"fixture_id": fixture_id})
        )

    def load_bet365_prematch(self) -> dict:
        return self._unwrap_data_dict(self.http.get_data("/api/odds/bet365-prematch"))

    def load_selected_fixture_odds(self, home: str, away: str) -> dict:
        return self._unwrap_data_dict(
            self.http.get_data("/api/odds/selected-fixture", params={"home": home, "away": away})
        )

    def load_team_advanced_form(self, home: str, away: str, competition: Optional[str] = None) -> dict:
        comp = competition or self.cfg.competition
        data = self._unwrap_data_dict(
            self.http.get_data(
                "/api/advanced/team-form",
                params={"competition": comp, "home": home, "away": away},
            )
        )
        return data or {"home": {}, "away": {}}

    def load_probable_lineups(self, home: str, away: str, competition: Optional[str] = None) -> dict:
        comp = competition or self.cfg.competition
        data = self._unwrap_data_dict(
            self.http.get_data(
                "/api/advanced/probable-lineups",
                params={"competition": comp, "home": home, "away": away},
            )
        )
        return data or {"home": {}, "away": {}}

    def load_injury_report(self, home: str, away: str, competition: Optional[str] = None) -> dict:
        comp = competition or self.cfg.competition
        data = self._unwrap_data_dict(
            self.http.get_data(
                "/api/advanced/injuries",
                params={"competition": comp, "home": home, "away": away},
            )
        )
        return data or {"home": {}, "away": {}}

    def load_rest_profile(self, home: str, away: str, competition: Optional[str] = None) -> dict:
        comp = competition or self.cfg.competition
        data = self._unwrap_data_dict(
            self.http.get_data(
                "/api/advanced/rest-profile",
                params={"competition": comp, "home": home, "away": away},
            )
        )
        return data or {"home": {}, "away": {}}

    def load_odds_movement(self, home: str, away: str, competition: Optional[str] = None) -> dict:
        comp = competition or self.cfg.competition
        return self._unwrap_data_dict(
            self.http.get_data(
                "/api/advanced/odds-movement",
                params={"competition": comp, "home": home, "away": away},
            )
        )

    def load_live_match_events(self, home: str, away: str, competition: Optional[str] = None) -> dict:
        comp = competition or self.cfg.competition
        return self._unwrap_data_dict(
            self.http.get_data(
                "/api/advanced/live-events",
                params={"competition": comp, "home": home, "away": away},
            )
        )

    def load_player_form(self, home: str, away: str, competition: Optional[str] = None) -> dict:
        comp = competition or self.cfg.competition
        data = self._unwrap_data_dict(
            self.http.get_data(
                "/api/advanced/player-form",
                params={"competition": comp, "home": home, "away": away},
            )
        )
        return data or {"home": {}, "away": {}}

    def load_tactical_matchup(self, home: str, away: str, competition: Optional[str] = None) -> dict:
        comp = competition or self.cfg.competition
        return self._unwrap_data_dict(
            self.http.get_data(
                "/api/advanced/tactical-matchup",
                params={"competition": comp, "home": home, "away": away},
            )
        )

    def load_match_intelligence(self, home: str, away: str, competition: Optional[str] = None) -> dict:
        comp = competition or self.cfg.competition
        return {
            "team_advanced_form": self.load_team_advanced_form(home, away, comp),
            "probable_lineups": self.load_probable_lineups(home, away, comp),
            "injury_report": self.load_injury_report(home, away, comp),
            "rest_profile": self.load_rest_profile(home, away, comp),
            "odds_movement": self.load_odds_movement(home, away, comp),
            "live_match_events": self.load_live_match_events(home, away, comp),
            "player_form": self.load_player_form(home, away, comp),
            "tactical_matchup": self.load_tactical_matchup(home, away, comp),
        }


def _fallback_compute_form_from_fixtures(fixtures: list[dict], *, team: str, competition: str) -> dict:
    finished = []
    for match in fixtures or []:
        if match.get("status") != "FINISHED":
            continue
        if team not in (match.get("home"), match.get("away")):
            continue
        if "homeGoals" not in match or "awayGoals" not in match:
            continue
        finished.append(match)

    finished.sort(key=lambda x: x.get("utcDate") or "", reverse=True)

    sequence: list[str] = []
    wins_recent = 0
    draws_recent = 0
    losses_recent = 0
    gf_total = 0
    ga_total = 0

    for match in finished[:10]:
        home_name = match.get("home")
        hg = int(match.get("homeGoals"))
        ag = int(match.get("awayGoals"))

        if team == home_name:
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
