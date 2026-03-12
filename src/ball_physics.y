import math


class BallPhysics:

    def __init__(self):

        self.dx = 0
        self.dy = 0
        self.friction = 0.96

    def kick(self, start, target, power=8):

        sx, sy = start
        tx, ty = target

        dx = tx - sx
        dy = ty - sy

        dist = math.hypot(dx, dy) + 0.0001

        self.dx = dx / dist * power
        self.dy = dy / dist * power

    def update(self):

        self.dx *= self.friction
        self.dy *= self.friction

        return self.dx, self.dy