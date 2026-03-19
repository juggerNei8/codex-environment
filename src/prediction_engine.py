from __future__ import annotations

from typing import Any, Dict, List, Tuple


class PredictionEngine:
    def __init__(self) -> None:
        self.minimum_pct = 8
        self.maximum_pct = 78

    def build_prediction(
        self,
        home: str,
        away: str,
        home_form: Dict[str, Any] | None = None,
        away_form: Dict[str, Any] | None = None,
        live_games: Dict[str, Any] | None = None,
        prematch_summary: Dict[str, Any] | None = None,
        tournament_odds: Dict[str, Any] | None = None,
        fixture_odds: Dict[str, Any] | None = None,
        team_advanced_form: Dict[str, Any] | None = None,
        probable_lineups: Dict[str, Any] | None = None,
        injury_report: Dict[str, Any] | None = None,
        rest_profile: Dict[str, Any] | None = None,
        odds_movement: Dict[str, Any] | None = None,
        live_match_events: Dict[str, Any] | None = None,
        player_form: Dict[str, Any] | None = None,
        tactical_matchup: Dict[str, Any] | None = None,
    ) -> str:
        model = self._build_model(
            home=home,
            away=away,
            home_form=home_form or {},
            away_form=away_form or {},
            live_games=live_games or {},
            prematch_summary=prematch_summary or {},
            tournament_odds=tournament_odds or {},
            fixture_odds=fixture_odds or {},
            team_advanced_form=team_advanced_form or {},
            probable_lineups=probable_lineups or {},
            injury_report=injury_report or {},
            rest_profile=rest_profile or {},
            odds_movement=odds_movement or {},
            live_match_events=live_match_events or {},
            player_form=player_form or {},
            tactical_matchup=tactical_matchup or {},
        )
        verdict = self._pick_verdict(home, away, model["home_pct"], model["draw_pct"], model["away_pct"])
        confidence = self._build_confidence_label(model["confidence_score"])
        return (
            f"Prediction: {home} {model['home_pct']}% | Draw {model['draw_pct']}% | "
            f"{away} {model['away_pct']}% | {verdict} | Confidence: {confidence} | "
            f"Edge {model['edge_points']:+.1f}"
        )

    def build_prediction_block(self, **kwargs) -> str:
        model = self._build_model(**kwargs)
        home = kwargs["home"]
        away = kwargs["away"]
        lines = [
            f"{home} vs {away}",
            f"Win model: {home} {model['home_pct']}% | Draw {model['draw_pct']}% | {away} {model['away_pct']}%",
            f"Confidence: {self._build_confidence_label(model['confidence_score'])} ({model['confidence_score']:.0f}/100)",
            f"Primary verdict: {self._pick_verdict(home, away, model['home_pct'], model['draw_pct'], model['away_pct'])}",
            f"Model edge points: {model['edge_points']:+.1f}",
            "",
            "Factor scores",
        ]
        for key, value in model["components"].items():
            lines.append(f"- {key}: {value:+.2f}")
        lines.append("")
        lines.append("Reason summary")
        for reason in model["reasons"]:
            lines.append(f"- {reason}")
        return "\n".join(lines)

    def build_odds_caption(self, fixture_odds: Dict[str, Any] | None = None) -> str:
        fixture_odds = fixture_odds or {}
        selected = fixture_odds.get("selected", {}) if isinstance(fixture_odds, dict) else {}
        if not isinstance(selected, dict) or not selected:
            return "Odds: unavailable"
        return f"Odds: H {selected.get('home', '-')} | D {selected.get('draw', '-')} | A {selected.get('away', '-')}"

    def _build_model(self, **kwargs) -> Dict[str, Any]:
        home_form = kwargs["home_form"]
        away_form = kwargs["away_form"]
        live_games = kwargs["live_games"]
        prematch_summary = kwargs["prematch_summary"]
        tournament_odds = kwargs["tournament_odds"]
        fixture_odds = kwargs["fixture_odds"]
        team_advanced_form = kwargs["team_advanced_form"]
        probable_lineups = kwargs["probable_lineups"]
        injury_report = kwargs["injury_report"]
        rest_profile = kwargs["rest_profile"]
        odds_movement = kwargs["odds_movement"]
        live_match_events = kwargs["live_match_events"]
        player_form = kwargs["player_form"]
        tactical_matchup = kwargs["tactical_matchup"]

        base_form_edge = (self._team_form_score(home_form) - self._team_form_score(away_form)) / 12.0
        xg_edge = self._xg_edge(team_advanced_form)
        lineup_edge = self._lineup_edge(probable_lineups)
        injury_edge = self._injury_edge(injury_report)
        rest_edge = self._rest_edge(rest_profile)
        odds_edge = self._odds_edge(fixture_odds)
        odds_move_edge = self._odds_movement_edge(odds_movement)
        player_form_edge = self._player_form_edge(player_form)
        tactical_edge = self._tactical_edge(tactical_matchup)
        live_events_edge = self._live_events_edge(live_games, live_match_events)
        tournament_edge = 0.15 if isinstance(tournament_odds, dict) and tournament_odds.get("summary") else 0.0
        prematch_edge = self._prematch_market_edge(prematch_summary)

        edge_points = (
            base_form_edge + xg_edge + lineup_edge + injury_edge + rest_edge +
            odds_edge + odds_move_edge + player_form_edge + tactical_edge +
            live_events_edge + tournament_edge + prematch_edge
        )
        home_pct, draw_pct, away_pct = self._edge_to_percentages(edge_points)
        confidence_score = self._confidence_score(
            edge_points,
            fixture_odds,
            probable_lineups,
            injury_report,
            team_advanced_form,
            live_match_events,
            odds_movement,
        )
        reasons = self._reason_lines(
            xg_edge,
            lineup_edge,
            injury_edge,
            rest_edge,
            odds_edge + odds_move_edge,
            player_form_edge,
            tactical_edge,
            live_events_edge,
        )
        return {
            "home_pct": home_pct,
            "draw_pct": draw_pct,
            "away_pct": away_pct,
            "confidence_score": confidence_score,
            "edge_points": edge_points,
            "components": {
                "base_form": base_form_edge,
                "xg_edge": xg_edge,
                "lineup_edge": lineup_edge,
                "injury_edge": injury_edge,
                "rest_edge": rest_edge,
                "odds_edge": odds_edge,
                "odds_move_edge": odds_move_edge,
                "player_form_edge": player_form_edge,
                "tactical_edge": tactical_edge,
                "live_events_edge": live_events_edge,
            },
            "reasons": reasons,
        }

    def _team_form_score(self, form: Dict[str, Any]) -> float:
        wins_recent = self._to_float(form.get("wins_recent", 0))
        draws_recent = self._to_float(form.get("draws_recent", 0))
        losses_recent = self._to_float(form.get("losses_recent", 0))
        goals_for_recent = self._to_float(form.get("goals_for_recent", 0))
        goals_against_recent = self._to_float(form.get("goals_against_recent", 0))
        morale = self._normalize_morale(form.get("morale", 0.5))
        form_last5 = form.get("form_last5", []) or []
        form_points = 0.0
        for item in form_last5:
            item = str(item).strip().upper()
            if item == "W":
                form_points += 1.5
            elif item == "D":
                form_points += 0.7
            elif item == "L":
                form_points -= 1.1
        score = 50.0 + wins_recent * 3.4 + draws_recent * 1.0 - losses_recent * 2.9
        score += goals_for_recent * 0.60 - goals_against_recent * 0.48 + form_points
        score += (morale - 0.5) * 12.0
        return score

    def _xg_edge(self, data: Dict[str, Any]) -> float:
        home = data.get("home", {}) if isinstance(data, dict) else {}
        away = data.get("away", {}) if isinstance(data, dict) else {}
        home_strength = self._to_float(home.get("xg_for_5", home.get("xg_for", 0))) - self._to_float(home.get("xga_5", home.get("xga", 0)))
        away_strength = self._to_float(away.get("xg_for_5", away.get("xg_for", 0))) - self._to_float(away.get("xga_5", away.get("xga", 0)))
        return (home_strength - away_strength) * 1.35

    def _lineup_edge(self, data: Dict[str, Any]) -> float:
        home = data.get("home", {}) if isinstance(data, dict) else {}
        away = data.get("away", {}) if isinstance(data, dict) else {}
        strength_edge = (self._to_float(home.get("strength_score", 0)) - self._to_float(away.get("strength_score", 0))) * 0.18
        absence_edge = (self._to_float(home.get("key_absent_count", 0)) - self._to_float(away.get("key_absent_count", 0))) * 0.9
        return strength_edge - absence_edge

    def _injury_edge(self, data: Dict[str, Any]) -> float:
        home = data.get("home", {}) if isinstance(data, dict) else {}
        away = data.get("away", {}) if isinstance(data, dict) else {}
        return (self._to_float(away.get("impact_score", 0)) - self._to_float(home.get("impact_score", 0))) * 0.55

    def _rest_edge(self, data: Dict[str, Any]) -> float:
        home = data.get("home", {}) if isinstance(data, dict) else {}
        away = data.get("away", {}) if isinstance(data, dict) else {}
        return ((self._to_float(home.get("days_rest", 0)) - self._to_float(away.get("days_rest", 0))) * 0.22) + ((self._to_float(away.get("fatigue_score", 0)) - self._to_float(home.get("fatigue_score", 0))) * 0.40)

    def _odds_edge(self, fixture_odds: Dict[str, Any]) -> float:
        selected = fixture_odds.get("selected", {}) if isinstance(fixture_odds, dict) else {}
        if not isinstance(selected, dict) or not selected:
            return 0.0
        home_odds = self._safe_decimal(selected.get("home"))
        away_odds = self._safe_decimal(selected.get("away"))
        if home_odds is None or away_odds is None:
            return 0.0
        return ((1.0 / max(home_odds, 1.01)) - (1.0 / max(away_odds, 1.01))) * 24.0

    def _odds_movement_edge(self, data: Dict[str, Any]) -> float:
        if not isinstance(data, dict):
            return 0.0
        return ((-self._to_float(data.get("home_move_pct", 0))) - (-self._to_float(data.get("away_move_pct", 0)))) * 0.08

    def _player_form_edge(self, data: Dict[str, Any]) -> float:
        if not isinstance(data, dict):
            return 0.0
        home = data.get("home", {}) or {}
        away = data.get("away", {}) or {}
        return ((self._to_float(home.get("attack_form", 0)) + self._to_float(home.get("defense_form", 0))) - (self._to_float(away.get("attack_form", 0)) + self._to_float(away.get("defense_form", 0)))) * 0.14

    def _tactical_edge(self, data: Dict[str, Any]) -> float:
        if not isinstance(data, dict):
            return 0.0
        return self._to_float(data.get("home_edge_score", 0)) - self._to_float(data.get("away_edge_score", 0))

    def _live_events_edge(self, live_games: Dict[str, Any], live_match_events: Dict[str, Any]) -> float:
        edge = 0.0
        if isinstance(live_match_events, dict):
            edge += (self._to_float(live_match_events.get("home_xg_live", 0)) - self._to_float(live_match_events.get("away_xg_live", 0))) * 0.75
            edge += (self._to_float(live_match_events.get("home_momentum", 0)) - self._to_float(live_match_events.get("away_momentum", 0))) * 0.05
            edge += (self._to_float(live_match_events.get("away_cards", 0)) - self._to_float(live_match_events.get("home_cards", 0))) * 0.20
        return edge

    def _prematch_market_edge(self, data: Dict[str, Any]) -> float:
        if not isinstance(data, dict):
            return 0.0
        summary = data.get("summary", {}) or {}
        return min(0.6, self._to_float(summary.get("event_count", 0)) * 0.01)

    def _edge_to_percentages(self, edge_points: float) -> Tuple[int, int, int]:
        base_home = 45 + int(edge_points * 2.2)
        base_home = max(self.minimum_pct, min(self.maximum_pct, base_home))
        closeness = max(0, 18 - int(abs(edge_points) * 1.7))
        draw_pct = max(10, min(28, 12 + closeness))
        away_pct = 100 - base_home - draw_pct
        if away_pct < self.minimum_pct:
            shortage = self.minimum_pct - away_pct
            away_pct = self.minimum_pct
            base_home = max(self.minimum_pct, base_home - shortage)
        total = base_home + draw_pct + away_pct
        if total != 100:
            base_home += 100 - total
        return int(base_home), int(draw_pct), int(away_pct)

    def _confidence_score(
        self,
        edge_points: float,
        fixture_odds: Dict[str, Any],
        probable_lineups: Dict[str, Any],
        injury_report: Dict[str, Any],
        team_advanced_form: Dict[str, Any],
        live_match_events: Dict[str, Any],
        odds_movement: Dict[str, Any],
    ) -> float:
        score = 42.0 + min(20.0, abs(edge_points) * 3.2)
        if isinstance(fixture_odds, dict) and fixture_odds.get("selected"):
            score += 12.0
        if isinstance(probable_lineups, dict) and (probable_lineups.get("home") or probable_lineups.get("away")):
            score += 8.0
        if isinstance(injury_report, dict) and (injury_report.get("home") or injury_report.get("away")):
            score += 8.0
        if isinstance(team_advanced_form, dict) and (team_advanced_form.get("home") or team_advanced_form.get("away")):
            score += 8.0
        if isinstance(odds_movement, dict) and odds_movement:
            score += 5.0
        if isinstance(live_match_events, dict) and live_match_events:
            score += 7.0
        return max(30.0, min(96.0, score))

    def _build_confidence_label(self, score: float) -> str:
        if score >= 82:
            return "high"
        if score >= 62:
            return "medium"
        return "low"

    def _pick_verdict(self, home: str, away: str, home_pct: int, draw_pct: int, away_pct: int) -> str:
        if home_pct >= away_pct and home_pct >= draw_pct:
            return f"Likely winner: {home}" if (home_pct - away_pct) >= 10 else f"Edge: {home}"
        if away_pct >= home_pct and away_pct >= draw_pct:
            return f"Likely winner: {away}" if (away_pct - home_pct) >= 10 else f"Edge: {away}"
        return "Draw is live"

    def _reason_lines(
        self,
        xg_edge: float,
        lineup_edge: float,
        injury_edge: float,
        rest_edge: float,
        odds_edge: float,
        player_form_edge: float,
        tactical_edge: float,
        live_events_edge: float,
    ) -> List[str]:
        reasons: List[str] = []
        if xg_edge > 0.35:
            reasons.append("home xG profile stronger")
        elif xg_edge < -0.35:
            reasons.append("away xG profile stronger")
        if lineup_edge > 0.25:
            reasons.append("home projected lineup stronger")
        elif lineup_edge < -0.25:
            reasons.append("away projected lineup stronger")
        if injury_edge > 0.20:
            reasons.append("away availability issues heavier")
        elif injury_edge < -0.20:
            reasons.append("home availability issues heavier")
        if rest_edge > 0.18:
            reasons.append("home rest and fatigue edge")
        elif rest_edge < -0.18:
            reasons.append("away rest and fatigue edge")
        if odds_edge > 0.25:
            reasons.append("market supports home side")
        elif odds_edge < -0.25:
            reasons.append("market supports away side")
        if player_form_edge > 0.20:
            reasons.append("home player form stronger")
        elif player_form_edge < -0.20:
            reasons.append("away player form stronger")
        if tactical_edge > 0.20:
            reasons.append("tactical matchup favors home")
        elif tactical_edge < -0.20:
            reasons.append("tactical matchup favors away")
        if live_events_edge > 0.25:
            reasons.append("live event flow favors home")
        elif live_events_edge < -0.25:
            reasons.append("live event flow favors away")
        if not reasons:
            reasons.append("limited model separation")
        return reasons[:6]

    def _to_float(self, value: Any) -> float:
        try:
            return float(value)
        except Exception:
            return 0.0

    def _normalize_morale(self, value: Any) -> float:
        try:
            morale = float(value)
        except Exception:
            morale = 0.5
        if morale > 1.0:
            morale = morale / 100.0
        return max(0.0, min(1.0, morale))

    def _safe_decimal(self, value: Any) -> float | None:
        try:
            number = float(value)
            return number if number > 0 else None
        except Exception:
            return None
