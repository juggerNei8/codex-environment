import random
import pandas as pd
import os


class SeasonEngine:
    def __init__(self):
        self.teams = []
        self.fixtures = []
        self.table = {}

    def load_teams(self, teams):
        self.teams = list(teams)
        self.table = {
            t: {"played": 0, "wins": 0, "draws": 0, "losses": 0, "gd": 0, "points": 0}
            for t in self.teams
        }

    def generate_fixtures(self):
        self.fixtures = []
        for home in self.teams:
            for away in self.teams:
                if home != away:
                    self.fixtures.append((home, away))

        random.shuffle(self.fixtures)

    def record_result(self, home, away, home_goals, away_goals):
        self.table[home]["played"] += 1
        self.table[away]["played"] += 1
        self.table[home]["gd"] += (home_goals - away_goals)
        self.table[away]["gd"] += (away_goals - home_goals)

        if home_goals > away_goals:
            self.table[home]["wins"] += 1
            self.table[home]["points"] += 3
            self.table[away]["losses"] += 1
        elif away_goals > home_goals:
            self.table[away]["wins"] += 1
            self.table[away]["points"] += 3
            self.table[home]["losses"] += 1
        else:
            self.table[home]["draws"] += 1
            self.table[away]["draws"] += 1
            self.table[home]["points"] += 1
            self.table[away]["points"] += 1

    def save_table_csv(self, database_dir):
        rows = []
        for team, stats in self.table.items():
            rows.append({
                "team": team,
                "played": stats["played"],
                "wins": stats["wins"],
                "draws": stats["draws"],
                "losses": stats["losses"],
                "gd": stats["gd"],
                "points": stats["points"]
            })

        df = pd.DataFrame(rows).sort_values(["points", "gd"], ascending=[False, False])
        os.makedirs(database_dir, exist_ok=True)
        df.to_csv(os.path.join(database_dir, "league_table.csv"), index=False)