import pandas as pd
import random

teams = pd.read_csv("database/teams.csv")

def predict_match(team1, team2):

    t1 = teams[teams["team"] == team1].iloc[0]
    t2 = teams[teams["team"] == team2].iloc[0]

    score1 = int((t1.attack + random.randint(0,10)) / 20)
    score2 = int((t2.attack + random.randint(0,10)) / 20)

    win_prob1 = round(random.uniform(40,60),2)
    win_prob2 = 100 - win_prob1

    return score1, score2, win_prob1, win_prob2