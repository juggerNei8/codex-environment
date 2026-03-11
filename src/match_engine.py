import random
import pandas as pd
from utils import resource_path

teams = pd.read_csv(resource_path("database/teams.csv"))
players = pd.read_csv(resource_path("database/players.csv"))

def get_team_strength(team):

    team_data = teams.loc[teams['team'] == team]

    if team_data.empty:
        return 70

    base_strength = team_data['strength'].values[0]

    team_players = players.loc[players['team'] == team]

    if team_players.empty:
        return base_strength

    avg_rating = team_players['rating'].mean()

    return (base_strength * 0.6) + (avg_rating * 0.4)


def simulate_match(team1, team2):

    strength1 = get_team_strength(team1)
    strength2 = get_team_strength(team2)

    possession1 = strength1 / (strength1 + strength2)
    possession2 = 1 - possession1

    shots1 = int(random.gauss(10 * possession1 + 5, 2))
    shots2 = int(random.gauss(10 * possession2 + 5, 2))

    xg1 = shots1 * random.uniform(0.08, 0.18)
    xg2 = shots2 * random.uniform(0.08, 0.18)

    goals1 = 0
    goals2 = 0

    timeline = []

    for minute in range(1, 91):

        if random.random() < xg1 / 90:
            goals1 += 1
            timeline.append(f"{minute}' GOAL {team1}")

        if random.random() < xg2 / 90:
            goals2 += 1
            timeline.append(f"{minute}' GOAL {team2}")

    return {
        "score": f"{team1} {goals1} - {goals2} {team2}",
        "possession": (round(possession1*100), round(possession2*100)),
        "shots": (shots1, shots2),
        "xg": (round(xg1,2), round(xg2,2)),
        "timeline": timeline
    }