from dataclasses import dataclass


@dataclass
class ManagerDecision:
    formation: str
    press_intensity: float
    tempo: float
    directness: float
    attacking_width: float
    risk_level: float
    notes: str


class ManagerAI:
    """
    Turns context into tactical decisions.
    """

    def choose_tactics(
        self,
        strength_gap: float,
        morale_gap: float,
        fatigue_level: float,
        need_goal: bool = False,
    ) -> ManagerDecision:
        if need_goal:
            return ManagerDecision(
                formation="4-2-3-1",
                press_intensity=0.78,
                tempo=0.76,
                directness=0.68,
                attacking_width=0.72,
                risk_level=0.81,
                notes="Chasing the match, pushing higher with extra attacking support.",
            )

        if fatigue_level > 0.55:
            return ManagerDecision(
                formation="4-3-3",
                press_intensity=0.46,
                tempo=0.48,
                directness=0.42,
                attacking_width=0.55,
                risk_level=0.38,
                notes="Energy conservation mode, lower press and safer build-up.",
            )

        if strength_gap > 4 or morale_gap > 0.08:
            return ManagerDecision(
                formation="4-3-3",
                press_intensity=0.66,
                tempo=0.63,
                directness=0.55,
                attacking_width=0.64,
                risk_level=0.58,
                notes="Positive approach with stable midfield control.",
            )

        return ManagerDecision(
            formation="4-2-3-1",
            press_intensity=0.58,
            tempo=0.56,
            directness=0.52,
            attacking_width=0.60,
            risk_level=0.50,
            notes="Balanced setup focused on structure and controlled progression.",
        )