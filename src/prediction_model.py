# src/prediction_model.py
import pandas as pd
from utils import resource_path

teams_csv = resource_path("database/teams.csv")
players_csv = resource_path("database/players.csv")

try:
    teams = pd.read_csv(teams_csv)
    players = pd.read_csv(players_csv)
except FileNotFoundError as e:
    raise FileNotFoundError(f"CSV not found: {e}")

def predict_match(team1, team2):
    t1_score = teams.loc[teams['team'] == team1, 'strength'].values[0]
    t2_score = teams.loc[teams['team'] == team2, 'strength'].values[0]
    if t1_score > t2_score:
        return f"{team1} wins!"
    elif t2_score > t1_score:
        return f"{team2} wins!"
    else:
        return "Draw!"