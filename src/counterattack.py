import random

def counter_attack(speed):

    if random.random() < speed * 0.02:
        return True

    return False