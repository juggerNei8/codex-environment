class ManagerAI:
    """
    Chooses live tactical adjustments based on score, stamina, and possession.
    """

    def __init__(self):
        pass

    # ------------------------------------------------

    def decide(self, team_side, score_for, score_against, avg_stamina, possession_pct):
        trailing = score_for < score_against
        leading = score_for > score_against

        if trailing and avg_stamina > 58:
            return {
                "formation": "4-2-3-1",
                "press": 0.78,
                "pass_speed": 1.15,
                "shot_bias": 0.18,
                "shape": "attack"
            }

        if leading and avg_stamina < 60:
            return {
                "formation": "4-3-3",
                "press": 0.42,
                "pass_speed": 0.92,
                "shot_bias": 0.08,
                "shape": "protect"
            }

        if possession_pct < 46:
            return {
                "formation": "4-2-3-1",
                "press": 0.66,
                "pass_speed": 1.02,
                "shot_bias": 0.12,
                "shape": "recover"
            }

        return {
            "formation": "4-3-3",
            "press": 0.58,
            "pass_speed": 1.00,
            "shot_bias": 0.11,
            "shape": "balanced"
        }