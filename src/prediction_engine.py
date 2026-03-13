from __future__ import annotations

import math
import os
import pickle


class PredictionEngine:
    def __init__(self, model_path: str | None = None):
        self.model = None
        self.model_path = model_path

        if model_path and os.path.exists(model_path):
            try:
                with open(model_path, "rb") as f:
                    self.model = pickle.load(f)
            except Exception:
                self.model = None

    def sigmoid(self, x: float) -> float:
        return 1.0 / (1.0 + math.exp(-x))

    def heuristic_predict(self, features: dict) -> dict:
        score = (
            features["strength_gap"] * 0.11
            + features["form_gap"] * 0.20
            + features["goals_gap"] * 0.18
            + features["defense_gap"] * 0.12
            + features["shots_gap"] * 0.07
            + features["possession_gap"] * 0.06
            + features["manager_gap"] * 0.07
            + features["morale_gap"] * 0.18
            - features["injury_gap"] * 0.10
            + (features["atmosphere"] - 0.5) * 0.12
        )

        home_win = self.sigmoid(score)
        away_win = self.sigmoid(-score * 0.92)

        draw = max(0.10, 1.0 - abs(home_win - away_win) - 0.45)

        total = home_win + away_win + draw
        home_win /= total
        away_win /= total
        draw /= total

        return {
            "home_win": round(home_win, 4),
            "draw": round(draw, 4),
            "away_win": round(away_win, 4),
        }

    def ml_predict(self, features: dict) -> dict | None:
        if self.model is None:
            return None

        ordered = [[
            features["strength_gap"],
            features["form_gap"],
            features["goals_gap"],
            features["defense_gap"],
            features["shots_gap"],
            features["possession_gap"],
            features["manager_gap"],
            features["morale_gap"],
            features["injury_gap"],
            features["cards_pressure_gap"],
            features["tempo_factor"],
            features["atmosphere"],
            features["pitch_quality"],
            features["humidity"],
            features["temperature_c"],
            features["wind_kph"],
            features["odds_home_win"],
            features["odds_draw"],
            features["odds_away_win"],
            features["home_article_count"],
            features["away_article_count"],
            features["home_transfer_noise"],
            features["away_transfer_noise"],
        ]]

        try:
            probs = self.model.predict_proba(ordered)[0]
            # class order assumed [away_win, draw, home_win] or similar can vary;
            # adjust to your training setup later.
            if len(probs) >= 3:
                return {
                    "home_win": round(float(probs[2]), 4),
                    "draw": round(float(probs[1]), 4),
                    "away_win": round(float(probs[0]), 4),
                }
        except Exception:
            return None

        return None

    def predict(self, features: dict) -> dict:
        ml = self.ml_predict(features)
        if ml is not None:
            return ml
        return self.heuristic_predict(features)