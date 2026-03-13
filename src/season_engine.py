import os
import random
import pandas as pd
from pandas.errors import EmptyDataError


class SeasonEngine:
    def __init__(self):
        self.teams = []
        self.fixtures = []
        self.table = {}

    # ------------------------------------------------

    def load_teams_from_csv(self, database_dir):
        teams_path = os.path.join(database_dir, "teams.csv")

        if not os.path.exists(teams_path):
            self.teams = []
            self.table = {}
            return

        try:
            df = pd.read_csv(teams_path)
        except EmptyDataError:
            self.teams = []
            self.table = {}
            return

        if df.empty:
            self.teams = []
            self.table = {}
            return

        if "team" not in df.columns:
            first_col = df.columns[0]
            df = df.rename(columns={first_col: "team"})

        self.teams = sorted(df["team"].dropna().astype(str).unique().tolist())

        self.table = {
            t: {
                "played": 0,
                "wins": 0,
                "draws": 0,
                "losses": 0,
                "gd": 0,
                "points": 0
            }
            for t in self.teams
        }

    # ------------------------------------------------

    def generate_fixtures(self):
        self.fixtures = []

        for home in self.teams:
            for away in self.teams:
                if home != away:
                    self.fixtures.append((home, away))

        random.shuffle(self.fixtures)

    # ------------------------------------------------

    def load_fixtures_from_csv(self, database_dir):
        fixtures_path = os.path.join(database_dir, "fixtures.csv")

        if not os.path.exists(fixtures_path):
            self.generate_fixtures()
            return

        try:
            df = pd.read_csv(fixtures_path)
        except EmptyDataError:
            self.generate_fixtures()
            return
        except Exception:
            self.generate_fixtures()
            return

        if df.empty:
            self.generate_fixtures()
            return

        if "home" in df.columns and "away" in df.columns:
            self.fixtures = list(zip(df["home"], df["away"]))
        else:
            self.generate_fixtures()

    # ------------------------------------------------

    def record_result(self, home, away, home_goals, away_goals):
        if home not in self.table or away not in self.table:
            return

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

    # ------------------------------------------------

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
                "points": stats["points"],
            })

        df = pd.DataFrame(rows)

        if not df.empty:
            df = df.sort_values(["points", "gd"], ascending=[False, False])

        out = os.path.join(database_dir, "league_table.csv")
        df.to_csv(out, index=False)

    # ------------------------------------------------

    def save_fixtures_csv(self, database_dir):
        out = os.path.join(database_dir, "fixtures.csv")

        rows = [{"home": home, "away": away, "competition": "League"} for home, away in self.fixtures]
        df = pd.DataFrame(rows)
        df.to_csv(out, index=False)