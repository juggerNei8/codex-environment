import random


class AIManager:

    def __init__(self, team):

        self.team = team

        self.tactics = random.choice([
            "attacking",
            "balanced",
            "defensive"
        ])

    def make_decision(self):

        if self.tactics == "attacking":
            return "shoot"

        if self.tactics == "defensive":
            return "pass"

        return random.choice(["pass", "shoot"])