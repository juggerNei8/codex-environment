import random
import pandas as pd
from utils import resource_path
from formations import FORMATIONS
from injuries import injury_check
from substitution import should_substitute
from counterattack import counter_attack

# Load databases
teams = pd.read_csv(resource_path("database/teams.csv"))
players = pd.read_csv(resource_path("database/players.csv"))

MATCH_MINUTES = 90


# ---------------------------
# TEAM DATA
# ---------------------------

def team_strength(team_id):

    team = teams[teams["team_id"] == team_id]

    if team.empty:
        return 70

    team = team.iloc[0]

    attack = team["attack"]
    midfield = team["midfield"]
    defense = team["defense"]

    return (attack + midfield + defense) / 3


def get_team_players(team_id):

    return players[players["team_id"] == team_id]


def player_attack_power(team_id):

    team_players = get_team_players(team_id)

    forwards = team_players[team_players["position"] == "FWD"]

    if forwards.empty:
        return 60

    return forwards["shooting"].mean()


def goalkeeper_skill(team_id):

    gk = players[
        (players["team_id"] == team_id) &
        (players["position"] == "GK")
    ]

    if gk.empty:
        return 70

    return gk.iloc[0]["gk_reflex"]


# ---------------------------
# MATCH LOGIC
# ---------------------------

def simulate_shot(att, defense, keeper):

    chance = max(0.05, (att - defense + 50) / 200)

    if random.random() < chance:

        distance = random.randint(5, 30)
        angle = random.randint(10, 90)

        xg = (0.35 * (1 - distance / 35) * (angle / 90))

        goal = random.random() > keeper / 120

        return goal, xg

    return None, 0


def simulate_possession(str1, str2):

    total = str1 + str2

    p1 = (str1 / total) * 100
    p2 = (str2 / total) * 100

    return round(p1), round(p2)


# ---------------------------
# MATCH ENGINE
# ---------------------------

def run_match(team1_id, team2_id, formation1="4-3-3", formation2="4-3-3"):

    base1 = team_strength(team1_id)
    base2 = team_strength(team2_id)

    attack1, defense1 = apply_formation(base1, formation1)
    attack2, defense2 = apply_formation(base2, formation2)

    keeper1 = goalkeeper_skill(team1_id)
    keeper2 = goalkeeper_skill(team2_id)

    possession = simulate_possession(base1, base2)

    score1 = 0
    score2 = 0

    stats = {
        "shots": [0, 0],
        "xg": [0, 0]
    }

    commentary = []

    for minute in range(1, MATCH_MINUTES + 1):

        # fatigue system
        fatigue1 = 1 - (minute / 200)
        fatigue2 = 1 - (minute / 200)

        attack1 *= fatigue1
        attack2 *= fatigue2

        # team1 attack
        goal, xg = simulate_shot(attack1, defense2, keeper2)

        if goal is not None:

            stats["shots"][0] += 1
            stats["xg"][0] += xg

            if goal:
                score1 += 1
                commentary.append(f"{minute}' GOAL Team1!")

        # team2 attack
        goal, xg = simulate_shot(attack2, defense1, keeper1)

        if goal is not None:

            stats["shots"][1] += 1
            stats["xg"][1] += xg

            if goal:
                score2 += 1
                commentary.append(f"{minute}' GOAL Team2!")

        # injury system
        if injury_check():
            commentary.append(f"{minute}' Player injured!")

        # substitution system
        if should_substitute(minute, 40):
            commentary.append(f"{minute}' Substitution made")

        # counter attack
        if counter_attack(80):
            commentary.append(f"{minute}' Dangerous counterattack!")

    result = {

        "score": [score1, score2],
        "possession": possession,
        "stats": stats,
        "commentary": commentary
    }

    return result


# ---------------------------
# FORMATIONS
# ---------------------------

def apply_formation(team_strength, formation):

    f = FORMATIONS.get(formation, FORMATIONS["4-3-3"])

    attack = team_strength * f["attack"]
    defense = team_strength * f["defense"]

    return attack, defense