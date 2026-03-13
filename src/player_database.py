import os
import pandas as pd
import random


class PlayerDatabase:
    def __init__(self):
        self.players = pd.DataFrame()

    # ------------------------------------------------

    def load_or_enrich(self, database_dir):
        teams_path = os.path.join(database_dir, "teams.csv")
        players_path = os.path.join(database_dir, "players.csv")

        if os.path.exists(players_path) and os.path.getsize(players_path) > 0:
            try:
                self.players = pd.read_csv(players_path)
            except Exception:
                self.players = pd.DataFrame()

        if self.players.empty:
            self.players = self.generate_from_teams(teams_path)
        else:
            self.players = self.enrich_existing(self.players, teams_path)

        self.players.to_csv(players_path, index=False)
        return self.players

    # ------------------------------------------------

    def generate_from_teams(self, teams_path):
        if not os.path.exists(teams_path):
            return pd.DataFrame(columns=["player", "team", "position", "rating", "value", "stamina"])

        teams_df = pd.read_csv(teams_path)
        if "team" not in teams_df.columns:
            first_col = teams_df.columns[0]
            teams_df = teams_df.rename(columns={first_col: "team"})

        template_positions = [
            "GK",
            "LB", "CB", "CB", "RB",
            "CM", "CM", "CAM",
            "LW", "ST", "RW",
            "CDM", "CM", "CB", "ST", "RW"
        ]

        rows = []
        for team in teams_df["team"].dropna().astype(str).tolist():
            base_strength = 75
            if "strength" in teams_df.columns:
                val = teams_df.loc[teams_df["team"] == team, "strength"]
                if not val.empty:
                    base_strength = int(val.iloc[0])

            for i, pos in enumerate(template_positions, start=1):
                rating = max(58, min(95, int(random.gauss(base_strength, 6))))
                value = int(max(1, rating - 50) * random.uniform(0.8, 2.5))
                rows.append({
                    "player": f"{team.replace(' ', '_')}_{pos}_{i}",
                    "team": team,
                    "position": pos,
                    "rating": rating,
                    "value": value,
                    "stamina": 100,
                    "injury_risk": round(random.uniform(0.02, 0.18), 3),
                    "form": round(random.uniform(0.45, 0.88), 3)
                })

        return pd.DataFrame(rows)

    # ------------------------------------------------

    def enrich_existing(self, df, teams_path):
        required = ["player", "team", "position", "rating", "value", "stamina", "injury_risk", "form"]
        for col in required:
            if col not in df.columns:
                if col == "value":
                    df[col] = 10
                elif col == "stamina":
                    df[col] = 100
                elif col == "injury_risk":
                    df[col] = 0.08
                elif col == "form":
                    df[col] = 0.60
                else:
                    df[col] = ""

        counts = df.groupby("team").size().to_dict()
        generated = self.generate_from_teams(teams_path)

        add_rows = []
        for team, team_df in generated.groupby("team"):
            current = counts.get(team, 0)
            if current < 14:
                need = 16 - current
                add_rows.extend(team_df.head(max(0, need)).to_dict("records"))

        if add_rows:
            df = pd.concat([df, pd.DataFrame(add_rows)], ignore_index=True)

        return df