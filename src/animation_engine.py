import random
from utils import resource_path


class AnimationEngine:

    def __init__(self, canvas):

        self.canvas = canvas

        self.players = []
        self.ball = None

        self.pitch_width = 900
        self.pitch_height = 500

        self.draw_pitch()

        self.create_players()
        self.create_ball()

    # -------------------------
    # DRAW PITCH
    # -------------------------

    def draw_pitch(self):

        self.canvas.create_rectangle(
            0, 0,
            self.pitch_width,
            self.pitch_height,
            fill="#2e7d32",
            outline=""
        )

        # midfield line
        self.canvas.create_line(
            self.pitch_width/2, 0,
            self.pitch_width/2, self.pitch_height,
            fill="white",
            width=2
        )

        # center circle
        self.canvas.create_oval(
            400,200,500,300,
            outline="white",
            width=2
        )

    # -------------------------
    # PLAYERS
    # -------------------------

    def create_players(self):

        # team 1 (red)
        for i in range(11):

            x = random.randint(80,350)
            y = random.randint(80,420)

            p = self.canvas.create_oval(
                x, y, x+16, y+16,
                fill="red",
                outline=""
            )

            self.players.append(p)

        # team 2 (blue)
        for i in range(11):

            x = random.randint(550,820)
            y = random.randint(80,420)

            p = self.canvas.create_oval(
                x, y, x+16, y+16,
                fill="blue",
                outline=""
            )

            self.players.append(p)

    # -------------------------
    # BALL
    # -------------------------

    def create_ball(self):

        self.ball = self.canvas.create_oval(
            440, 240, 452, 252,
            fill="white",
            outline="black"
        )

    # -------------------------
    # MOVEMENT
    # -------------------------

    def move_players(self):

        for p in self.players:

            dx = random.randint(-4,4)
            dy = random.randint(-4,4)

            self.canvas.move(p, dx, dy)

    def move_ball(self):

        dx = random.randint(-6,6)
        dy = random.randint(-6,6)

        self.canvas.move(self.ball, dx, dy)

    # -------------------------
    # MAIN ANIMATION LOOP
    # -------------------------

    def animate(self):

        self.move_players()
        self.move_ball()

        self.canvas.after(120, self.animate)