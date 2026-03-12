import random


class PlayerDatabase:

    def __init__(self):

        self.players = []

        self.generate_players()

    def generate_players(self):

        roles = [
            "ST","LW","RW",
            "CAM","CM","CDM",
            "CB","LB","RB",
            "GK"
        ]

        for i in range(20000):

            player = {
                "name": f"Player_{i}",
                "role": random.choice(roles),
                "rating": random.randint(60, 95),
                "value": random.randint(1, 120)
            }

            self.players.append(player)