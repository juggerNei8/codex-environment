import random


class MatchEngine:

    def __init__(self):

        self.attack_chance = 0.05
        self.shot_probability = 0.25

    # --------------------------------

    def simulate_event(self):

        r = random.random()

        if r < self.attack_chance:

            if random.random() < self.shot_probability:

                return self.shot_result()

            else:

                return "attack"

        return "pass"

    # --------------------------------

    def shot_result(self):

        r = random.random()

        if r < 0.15:
            return "goal"

        elif r < 0.45:
            return "save"

        else:
            return "miss"