import math


class PredictionEngine:
    def __init__(self):
        pass

    def sigmoid(self, x):
        return 1.0 / (1.0 + math.exp(-x))

    def predict_match(self, home_strength, away_strength, home_form, away_form, home_morale, away_morale):
        score = (
            (home_strength - away_strength) * 0.09 +
            (home_form - away_form) * 0.24 +
            (home_morale - away_morale) * 0.34
        )

        home_win = self.sigmoid(score)
        away_win = self.sigmoid(-score * 0.92)
        draw = max(0.12, 1.0 - abs(home_win - away_win) - 0.42)

        total = home_win + away_win + draw
        return {
            "home_win": round(home_win / total, 4),
            "draw": round(draw / total, 4),
            "away_win": round(away_win / total, 4)
        }

    def format_prediction(self, home, away, pred):
        return (
            f"[PREDICTION] {home} vs {away} | "
            f"Home {pred['home_win']:.0%} | "
            f"Draw {pred['draw']:.0%} | "
            f"Away {pred['away_win']:.0%}"
        )

    def format_post_match_reference(self, home, away, pred, home_score, away_score):
        return (
            f"[POST-MATCH MODEL] {home} {home_score}-{away_score} {away} | "
            f"Expected: Home {pred['home_win']:.0%}, Draw {pred['draw']:.0%}, Away {pred['away_win']:.0%}"
        )