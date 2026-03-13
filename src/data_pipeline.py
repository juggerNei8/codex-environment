from __future__ import annotations

import math
from dataclasses import dataclass

from article_ingestion import ArticleSignal
from environment_model import EnvironmentState


@dataclass
class TeamState:
    team: str
    strength: float
    form_last5: float
    goals_for_pg: float
    goals_against_pg: float
    shots_pg: float
    on_target_pg: float
    possession_pg: float
    injuries_count: int
    cards_pressure: float
    manager_rating: float
    transfer_noise: float = 0.0


class DataPipeline:
    """
    Normalizes raw match context into ML-friendly features.
    """

    def normalize(self, value: float, lo: float, hi: float) -> float:
        if hi <= lo:
            return 0.0
        return max(0.0, min(1.0, (value - lo) / (hi - lo)))

    def build_feature_vector(
        self,
        home: TeamState,
        away: TeamState,
        env: EnvironmentState,
        home_articles: ArticleSignal | None = None,
        away_articles: ArticleSignal | None = None,
        odds: dict | None = None,
    ) -> dict:
        home_articles = home_articles or ArticleSignal(home.team, 0, 0.0, 0.0, 0.0, 0.0, "")
        away_articles = away_articles or ArticleSignal(away.team, 0, 0.0, 0.0, 0.0, 0.0, "")
        odds = odds or {"home_win": 2.10, "draw": 3.30, "away_win": 3.10}

        strength_gap = home.strength - away.strength
        form_gap = home.form_last5 - away.form_last5
        goals_gap = home.goals_for_pg - away.goals_for_pg
        defense_gap = away.goals_against_pg - home.goals_against_pg
        shots_gap = home.shots_pg - away.shots_pg
        possession_gap = home.possession_pg - away.possession_pg
        manager_gap = home.manager_rating - away.manager_rating

        morale_home = env.morale_home + home_articles.morale_delta
        morale_away = env.morale_away + away_articles.morale_delta

        injury_pressure_home = self.normalize(home.injuries_count, 0, 8) + home_articles.injury_risk_delta
        injury_pressure_away = self.normalize(away.injuries_count, 0, 8) + away_articles.injury_risk_delta

        return {
            "strength_gap": strength_gap,
            "form_gap": form_gap,
            "goals_gap": goals_gap,
            "defense_gap": defense_gap,
            "shots_gap": shots_gap,
            "possession_gap": possession_gap,
            "manager_gap": manager_gap,
            "morale_gap": morale_home - morale_away,
            "injury_gap": injury_pressure_away - injury_pressure_home,
            "cards_pressure_gap": away.cards_pressure - home.cards_pressure,
            "tempo_factor": env.tempo_factor,
            "atmosphere": env.atmosphere,
            "pitch_quality": env.pitch_quality,
            "humidity": env.humidity,
            "temperature_c": env.temperature_c,
            "wind_kph": env.wind_kph,
            "odds_home_win": odds["home_win"],
            "odds_draw": odds["draw"],
            "odds_away_win": odds["away_win"],
            "home_article_count": home_articles.article_count,
            "away_article_count": away_articles.article_count,
            "home_transfer_noise": home_articles.transfer_noise,
            "away_transfer_noise": away_articles.transfer_noise,
        }