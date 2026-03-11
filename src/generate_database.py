import pandas as pd
import random
import os

# ensure database folder exists
os.makedirs("../database", exist_ok=True)

teams = []
players = []

leagues = [
    "Premier League",
    "La Liga",
    "Bundesliga",
    "Serie A",
    "Ligue 1",
    "MLS",
    "CAF Champions League",
    "Brazil Serie A"
]

for i in range(1, 501):
    team_name = f"Team{i}"
    league = random.choice(leagues)
    strength = random.randint(60, 95)

    teams.append([team_name, league, "Various", strength])

    for j in range(1, 23):
        player_name = f"{team_name}_Player{j}"
        rating = random.randint(60, 92)
        position = random.choice(["GK","CB","LB","RB","CM","CAM","LW","RW","ST"])

        players.append([player_name, team_name, position, rating])

teams_df = pd.DataFrame(teams, columns=["team","league","country","strength"])
players_df = pd.DataFrame(players, columns=["player","team","position","rating"])

teams_df.to_csv("../database/teams.csv", index=False)
players_df.to_csv("../database/players.csv", index=False)

print("✅ Database generated successfully")