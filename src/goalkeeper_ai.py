class GoalKeeperAI:

    def __init__(self, side):

        self.side = side

    def react(self, ball_x):

        if self.side == "left":
            goal_line = 20
        else:
            goal_line = 880

        if abs(ball_x - goal_line) < 120:
            return True

        return False