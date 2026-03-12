import random


class CommentaryEngine:
    def __init__(self):
        self.pass_lines = [
            "Crisp passing in midfield.",
            "Patient build-up play.",
            "Nice switch of play.",
            "Quick one-touch football.",
            "The team is probing for space."
        ]

        self.attack_lines = [
            "They are pushing forward with intent.",
            "Dangerous movement in the final third.",
            "The pressure is rising near the box.",
            "A clever attacking move is developing."
        ]

        self.shot_lines = [
            "Shot taken!",
            "A strike toward goal!",
            "They pull the trigger!",
            "A powerful effort!"
        ]

        self.save_lines = [
            "Excellent save by the goalkeeper!",
            "The keeper gets down quickly!",
            "Brilliant stop!",
            "Strong hands from the goalkeeper!"
        ]

        self.goal_lines = [
            "GOAL! The stadium erupts!",
            "GOAL! Clinical finish!",
            "GOAL! What a move!",
            "GOAL! A superb strike!"
        ]

        self.miss_lines = [
            "Just wide of the post.",
            "Over the bar.",
            "That one flashes past the target.",
            "A good effort, but off target."
        ]

    def pass_commentary(self):
        return random.choice(self.pass_lines)

    def attack_commentary(self):
        return random.choice(self.attack_lines)

    def shot_commentary(self):
        return random.choice(self.shot_lines)

    def save_commentary(self):
        return random.choice(self.save_lines)

    def goal_commentary(self):
        return random.choice(self.goal_lines)

    def miss_commentary(self):
        return random.choice(self.miss_lines)