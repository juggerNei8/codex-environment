def generate_commentary(event: str):
    return f"Commentary: {event} happened in the match!"
import random

goal_lines = [
"WHAT A GOAL!",
"Clinical finish!",
"Brilliant strike!",
"The keeper had no chance!"
]

shot_lines = [
"A powerful shot!",
"Just wide!",
"Great save by the goalkeeper!"
]

def generate_commentary(event):

    if "GOAL" in event:
        return random.choice(goal_lines)

    return random.choice(shot_lines)