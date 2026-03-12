import random
import math


class AnimationEngine:

    def __init__(self, canvas):

        self.canvas = canvas

        self.pitch_width = 900
        self.pitch_height = 500

        self.players = []
        self.ball = None

        self.ball_owner = None

        self.running = True

        self.draw_pitch()
        self.create_players()
        self.create_ball()

    # -------------------------
    # PITCH
    # -------------------------

    def draw_pitch(self):

        self.canvas.create_rectangle(
            0,0,self.pitch_width,self.pitch_height,
            fill="#2e7d32",outline=""
        )

        self.canvas.create_line(
            self.pitch_width/2,0,
            self.pitch_width/2,self.pitch_height,
            fill="white",width=2
        )

        self.canvas.create_oval(
            400,200,500,300,
            outline="white",width=2
        )

        # goals
        self.canvas.create_rectangle(0,200,20,300,outline="white",width=2)
        self.canvas.create_rectangle(880,200,900,300,outline="white",width=2)

    # -------------------------
    # 4-3-3 FORMATION
    # -------------------------

    def create_players(self):

        self.players.clear()

        formation_red = [
            (120,250), # GK
            (200,100),(200,200),(200,300),(200,400),
            (350,150),(350,250),(350,350),
            (520,120),(520,250),(520,380)
        ]

        formation_blue = [
            (780,250),
            (700,100),(700,200),(700,300),(700,400),
            (550,150),(550,250),(550,350),
            (380,120),(380,250),(380,380)
        ]

        for x,y in formation_red:

            p = self.canvas.create_oval(
                x,y,x+16,y+16,
                fill="red",outline=""
            )

            self.players.append(p)

        for x,y in formation_blue:

            p = self.canvas.create_oval(
                x,y,x+16,y+16,
                fill="blue",outline=""
            )

            self.players.append(p)

    # -------------------------
    # BALL
    # -------------------------

    def create_ball(self):

        self.ball = self.canvas.create_oval(
            440,240,452,252,
            fill="white",outline="black"
        )

    # -------------------------
    # PASSING SYSTEM
    # -------------------------

    def pass_ball(self):

        target = random.choice(self.players)

        tx,ty,_,_ = self.canvas.coords(target)
        bx,by,_,_ = self.canvas.coords(self.ball)

        dx = (tx-bx)/10
        dy = (ty-by)/10

        self.canvas.move(self.ball,dx,dy)

    # -------------------------
    # GOALKEEPER SAVE
    # -------------------------

    def goalkeeper_save(self):

        bx,by,_,_ = self.canvas.coords(self.ball)

        if bx < 40 or bx > 860:

            if random.random() < 0.6:

                self.canvas.move(self.ball,random.randint(-50,50),random.randint(-30,30))
                return True

        return False

    # -------------------------
    # GOAL DETECTION
    # -------------------------

    def check_goal(self):

        bx,by,_,_ = self.canvas.coords(self.ball)

        if bx <= 5:

            self.goal_animation("BLUE")

        if bx >= 895:

            self.goal_animation("RED")

    # -------------------------
    # GOAL ANIMATION
    # -------------------------

    def goal_animation(self,team):

        text = self.canvas.create_text(
            450,250,
            text=f"GOAL {team}!",
            fill="yellow",
            font=("Arial",28,"bold")
        )

        self.canvas.after(2000,lambda: self.canvas.delete(text))

        self.reset_positions()

    # -------------------------
    # RESET POSITIONS
    # -------------------------

    def reset_positions(self):

        for p in self.players:
            self.canvas.delete(p)

        self.canvas.delete(self.ball)

        self.create_players()
        self.create_ball()

    # -------------------------
    # PLAYER MOVEMENT
    # -------------------------

    def move_players(self):

        for p in self.players:

            dx = random.randint(-2,2)
            dy = random.randint(-2,2)

            x1,y1,x2,y2 = self.canvas.coords(p)

            if 0 < x1+dx < self.pitch_width:
                self.canvas.move(p,dx,0)

            if 0 < y1+dy < self.pitch_height:
                self.canvas.move(p,0,dy)

    # -------------------------
    # ANIMATION LOOP
    # -------------------------

    def animate(self):

        if not self.running:
            return

        self.move_players()

        if random.random() < 0.3:
            self.pass_ball()

        if not self.goalkeeper_save():
            self.check_goal()

        self.canvas.after(80,self.animate)