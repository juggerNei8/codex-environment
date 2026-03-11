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

    for minute in range(1, 90):

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
fatigue1 = 1 - (minute / 200)
fatigue2 = 1 - (minute / 200)

str1 *= fatigue1
str2 *= fatigue2
import random
import pandas as pd
from utils import resource_path

teams = pd.read_csv(resource_path("database/teams.csv"))
players = pd.read_csv(resource_path("database/players.csv"))

MATCH_MINUTES = 90


def get_team_players(team_id):
    return players[players["team_id"] == team_id]


def team_strength(team_id):

    team = teams[teams["team_id"] == team_id].iloc[0]

    attack = team["attack"]
    midfield = team["midfield"]
    defense = team["defense"]

    return (attack + midfield + defense) / 3


def simulate_possession(str1, str2):

    total = str1 + str2
    p1 = (str1 / total) * 100
    p2 = (str2 / total) * 100

    return round(p1), round(p2)


def shot_probability(att, defn):

    return max(0.05, (att - defn + 50) / 200)


def calculate_xg(distance, angle):

    base = 0.35
    distance_factor = max(0.1, 1 - distance / 35)
    angle_factor = angle / 90

    return base * distance_factor * angle_factor


def simulate_shot(team_attack, team_defense):

    prob = shot_probability(team_attack, team_defense)

    if random.random() < prob:

        distance = random.randint(5, 30)
        angle = random.randint(10, 90)

        xg = calculate_xg(distance, angle)

        goal = random.random() < xg

        return goal, xg

    return None, 0


def run_match(team1_id, team2_id):

    str1 = team_strength(team1_id)
    str2 = team_strength(team2_id)

    possession = simulate_possession(str1, str2)

    score1 = 0
    score2 = 0

    stats = {
        "shots":[0,0],
        "xg":[0,0]
    }

    commentary = []

    for minute in range(1, MATCH_MINUTES + 1):

        if random.random() < 0.18:

            goal,xg = simulate_shot(str1,str2)

            if goal is not None:

                stats["shots"][0]+=1
                stats["xg"][0]+=xg

                if goal:
                    score1+=1
                    commentary.append(f"{minute}' GOAL Team1! xG:{xg:.2f}")

        if random.random() < 0.18:

            goal,xg = simulate_shot(str2,str1)

            if goal is not None:

                stats["shots"][1]+=1
                stats["xg"][1]+=xg

                if goal:
                    score2+=1
                    commentary.append(f"{minute}' GOAL Team2! xG:{xg:.2f}")

    result = {
        "score":[score1,score2],
        "possession":possession,
        "stats":stats,
        "commentary":commentary
    }

    return result
import random
import pandas as pd
from utils import resource_path
teams = pd.read_csv(resource_path("database/teams.csv"))
players = pd.read_csv(resource_path("database/players.csv"))

MATCH_MINUTES = 90
def get_team_players(team_id):
    return players[players["team_id"] == team_id]
def player_attack_power(team_id):

    team_players = get_team_players(team_id)

    forwards = team_players[team_players["position"]=="FWD"]

    if len(forwards) == 0:
        return 50

    return forwards["shooting"].mean()
def goalkeeper_skill(team_id):

    gk = players[
        (players["team_id"]==team_id) &
        (players["position"]=="GK")
    ]

    if len(gk) == 0:
        return 70

    return gk.iloc[0]["gk_reflex"]
def goalkeeper_skill(team_id):

    gk = players[
        (players["team_id"]==team_id) &
        (players["position"]=="GK")
    ]

    if len(gk) == 0:
        return 70

    return gk.iloc[0]["gk_reflex"]
def simulate_shot(att,defn,keeper):

    chance = max(0.05,(att - defn + 50)/200)

    if random.random() < chance:

        xg = random.uniform(0.1,0.6)

        goal = random.random() > keeper/120

        return goal,xg

    return None,0
def run_match(team1_id,team2_id):

    str1 = team_strength(team1_id)
    str2 = team_strength(team2_id)

    keeper1 = goalkeeper_skill(team1_id)
    keeper2 = goalkeeper_skill(team2_id)

    score1 = 0
    score2 = 0

    commentary = []

    for minute in range(1,MATCH_MINUTES+1):

        goal,xg = simulate_shot(str1,str2,keeper2)

        if goal is not None:

            if goal:
                score1 += 1
                commentary.append(f"{minute}' GOAL Team1")

        goal,xg = simulate_shot(str2,str1,keeper1)

        if goal is not None:

            if goal:
                score2 += 1
                commentary.append(f"{minute}' GOAL Team2")

    return {
        "score":[score1,score2],
        "commentary":commentary
    }
from formations import FORMATIONS
def apply_formation(team_strength, formation):

    f = FORMATIONS[formation]

    attack = team_strength * f["attack"]
    defense = team_strength * f["defense"]

    return attack, defense
if injury_check():
    commentary.append(f"{minute}' Player injured!")
if should_substitute(minute,40):
    commentary.append(f"{minute}' Substitution made")
if counter_attack(80):
    commentary.append(f"{minute}' Dangerous counterattack!")