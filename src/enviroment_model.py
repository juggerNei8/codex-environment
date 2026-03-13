import math
import random
from dataclasses import dataclass


@dataclass
class EnvironmentState:
    stadium_name: str
    home_location: str
    temperature_c: float
    humidity: float
    wind_kph: float
    altitude_m: float
    crowd_intensity: float
    pitch_quality: float
    morale_home: float
    morale_away: float
    fatigue_home: float
    fatigue_away: float
    atmosphere: float
    tempo_factor: float


class EnvironmentModel:
    """
    Produces match-environment factors that can be used by:
    - prediction engine
    - manager AI
    - live commentary
    - simulation engine
    """

    def __init__(self):
        self.default_stadiums = {
            "Arsenal": ("Emirates Stadium", "London"),
            "Chelsea": ("Stamford Bridge", "London"),
            "Barcelona": ("Olympic Stadium", "Barcelona"),
            "Real Madrid": ("Santiago Bernabeu", "Madrid"),
            "Manchester City": ("Etihad Stadium", "Manchester"),
            "Liverpool": ("Anfield", "Liverpool"),
        }

    def build_environment(
        self,
        home_team: str,
        away_team: str,
        weather: dict | None = None,
        morale_home: float = 0.65,
        morale_away: float = 0.62,
        fatigue_home: float = 0.18,
        fatigue_away: float = 0.20,
        crowd_boost: float = 0.75,
    ) -> EnvironmentState:
        stadium_name, location = self.default_stadiums.get(
            home_team, ("Home Stadium", "Unknown")
        )

        if weather is None:
            weather = self.generate_default_weather()

        atmosphere = self.compute_atmosphere(
            crowd_boost=crowd_boost,
            morale_home=morale_home,
            venue_pressure=0.70,
        )

        tempo_factor = self.compute_tempo_factor(
            temperature_c=weather["temperature_c"],
            humidity=weather["humidity"],
            pitch_quality=weather["pitch_quality"],
            crowd_intensity=crowd_boost,
        )

        return EnvironmentState(
            stadium_name=stadium_name,
            home_location=location,
            temperature_c=weather["temperature_c"],
            humidity=weather["humidity"],
            wind_kph=weather["wind_kph"],
            altitude_m=weather["altitude_m"],
            crowd_intensity=crowd_boost,
            pitch_quality=weather["pitch_quality"],
            morale_home=morale_home,
            morale_away=morale_away,
            fatigue_home=fatigue_home,
            fatigue_away=fatigue_away,
            atmosphere=atmosphere,
            tempo_factor=tempo_factor,
        )

    def generate_default_weather(self) -> dict:
        return {
            "temperature_c": round(random.uniform(10, 28), 1),
            "humidity": round(random.uniform(45, 82), 1),
            "wind_kph": round(random.uniform(2, 22), 1),
            "altitude_m": round(random.uniform(5, 850), 1),
            "pitch_quality": round(random.uniform(0.72, 0.96), 2),
        }

    def compute_atmosphere(
        self,
        crowd_boost: float,
        morale_home: float,
        venue_pressure: float,
    ) -> float:
        val = 0.45 * crowd_boost + 0.30 * morale_home + 0.25 * venue_pressure
        return round(max(0.1, min(1.0, val)), 3)

    def compute_tempo_factor(
        self,
        temperature_c: float,
        humidity: float,
        pitch_quality: float,
        crowd_intensity: float,
    ) -> float:
        heat_penalty = max(0.0, (temperature_c - 22.0) * 0.01)
        humidity_penalty = max(0.0, (humidity - 65.0) * 0.003)
        pitch_bonus = (pitch_quality - 0.75) * 0.55
        crowd_bonus = crowd_intensity * 0.07

        tempo = 1.0 - heat_penalty - humidity_penalty + pitch_bonus + crowd_bonus
        return round(max(0.72, min(1.18, tempo)), 3)

    def to_feature_dict(self, env: EnvironmentState) -> dict:
        return {
            "temperature_c": env.temperature_c,
            "humidity": env.humidity,
            "wind_kph": env.wind_kph,
            "altitude_m": env.altitude_m,
            "crowd_intensity": env.crowd_intensity,
            "pitch_quality": env.pitch_quality,
            "morale_home": env.morale_home,
            "morale_away": env.morale_away,
            "fatigue_home": env.fatigue_home,
            "fatigue_away": env.fatigue_away,
            "atmosphere": env.atmosphere,
            "tempo_factor": env.tempo_factor,
        }