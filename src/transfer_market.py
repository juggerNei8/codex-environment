import random


class TransferMarket:
    def __init__(self):
        self.market = []

    def generate_mock_market(self, teams):
        positions = ["GK", "CB", "LB", "RB", "CDM", "CM", "CAM", "LW", "RW", "ST"]
        self.market = []

        for i in range(120):
            team = random.choice(teams) if teams else "Club"
            position = random.choice(positions)
            value = random.randint(2, 120)
            player = f"{position}_Player_{i}"

            self.market.append({
                "player": player,
                "team": team,
                "position": position,
                "value": value
            })