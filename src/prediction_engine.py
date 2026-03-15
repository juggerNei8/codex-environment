class PredictionEngine:
    def _avg_sample_strength(self, samples: list[dict]) -> float:
        if not samples:
            return 0.0

        total = 0.0
        count = 0

        for s in samples:
            try:
                h = float(s.get("home")) if s.get("home") is not None else None
                a = float(s.get("away")) if s.get("away") is not None else None
                d = float(s.get("draw")) if s.get("draw") is not None else None
            except Exception:
                h = a = d = None

            if h is not None and a is not None:
                total += (a - h) * 0.10
                count += 1

            if d is not None:
                total += max(-0.25, min(0.25, (3.2 - d) * 0.03))

        return total / count if count else 0.0

    def _selected_strength(self, fixture_odds: dict | None) -> tuple[float, str]:
        if not fixture_odds or not isinstance(fixture_odds, dict):
            return 0.0, ""

        selected = fixture_odds.get("selected")
        if not isinstance(selected, dict):
            return 0.0, ""

        strength = self._avg_sample_strength([selected])
        return strength, "selected-fixture"

    def build_prediction(
        self,
        home: str,
        away: str,
        home_form: dict,
        away_form: dict,
        live_games: dict | None = None,
        prematch_summary: dict | None = None,
        tournament_odds: dict | None = None,
        fixture_odds: dict | None = None,
    ) -> str:
        home_wins = int(home_form.get("wins_recent", 0))
        away_wins = int(away_form.get("wins_recent", 0))
        home_losses = int(home_form.get("losses_recent", 0))
        away_losses = int(away_form.get("losses_recent", 0))

        home_morale = float(home_form.get("morale", 0.5))
        away_morale = float(away_form.get("morale", 0.5))

        score = (
            (home_wins - away_wins) * 0.40
            - (home_losses - away_losses) * 0.25
            + (home_morale - away_morale) * 0.60
        )

        note_parts = []

        if prematch_summary and isinstance(prematch_summary, dict):
            summary = prematch_summary.get("summary", {}) or {}
            count = summary.get("event_count", 0)
            samples = summary.get("samples", []) or []
            if count:
                note_parts.append(f"bet365:{count}")
            score += self._avg_sample_strength(samples)

        if tournament_odds and isinstance(tournament_odds, dict):
            summary = tournament_odds.get("summary", {}) or {}
            count = summary.get("item_count", 0)
            samples = summary.get("samples", []) or []
            if count:
                note_parts.append(f"tournament:{count}")
            score += self._avg_sample_strength(samples)

        selected_strength, selected_note = self._selected_strength(fixture_odds)
        if selected_note:
            note_parts.append(selected_note)
            score += selected_strength * 1.5

        if live_games and isinstance(live_games, dict):
            live_count = len(live_games.get("live_matches", []) or [])
            if live_count:
                note_parts.append(f"live:{live_count}")

        home_pct = max(10, min(80, int(45 + score * 6)))
        away_pct = max(10, min(80, 100 - home_pct - 15))
        draw_pct = max(8, 100 - home_pct - away_pct)

        note = f" [{' | '.join(note_parts)}]" if note_parts else ""

        return f"Prediction: {home} {home_pct}% | Draw {draw_pct}% | {away} {away_pct}%{note}"