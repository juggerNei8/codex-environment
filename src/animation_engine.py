import random


class AnimationEngine:

    def __init__(self, canvas, commentary_callback=None,
                 goal_callback=None, possession_callback=None):

        self.canvas = canvas

        self.commentary = commentary_callback
        self.goal_callback = goal_callback
        self.possession_callback = possession_callback

        self.players = []
        self.ball = None

        self.running = False

        self.possession = {"red":0,"blue":0}

        self.pitch_w = 900
        self.pitch_h = 500

        self.draw_pitch()
        self.create_players()
        self.create_ball()

    # ------------------------------------------------

    def draw_pitch(self):

        self.canvas.create_rectangle(
            0,0,self.pitch_w,self.pitch_h,
            fill="#2e7d32",outline=""
        )

        self.canvas.create_line(
            self.pitch_w/2,0,self.pitch_w/2,self.pitch_h,
            fill="white",width=2
        )

        self.canvas.create_oval(
            400,200,500,300,
            outline="white",width=2
        )

        self.canvas.create_rectangle(0,210,10,290,fill="white")
        self.canvas.create_rectangle(890,210,900,290,fill="white")

    # ------------------------------------------------

    def create_players(self):

        formation_red = [
            (120,250),
            (250,100),(250,200),(250,300),(250,400),
            (400,150),(400,250),(400,350),
            (550,150),(550,250),(550,350)
        ]

        formation_blue = [
            (780,250),
            (650,100),(650,200),(650,300),(650,400),
            (500,150),(500,250),(500,350),
            (350,150),(350,250),(350,350)
        ]

        for x,y in formation_red:

            p=self.canvas.create_oval(x,y,x+16,y+16,fill="red")
            self.players.append(p)

        for x,y in formation_blue:

            p=self.canvas.create_oval(x,y,x+16,y+16,fill="blue")
            self.players.append(p)

    # ------------------------------------------------

    def create_ball(self):

        self.ball = self.canvas.create_oval(
            445,245,455,255,
            fill="white"
        )

    # ------------------------------------------------

    def move_players(self):

        for p in self.players:

            dx=random.randint(-2,2)
            dy=random.randint(-2,2)

            self.canvas.move(p,dx,dy)

    # ------------------------------------------------

    def pass_ball(self):

        players=self.players

        target=random.choice(players)

        px,py,_,_=self.canvas.coords(target)

        bx,by,_,_=self.canvas.coords(self.ball)

        dx=(px-bx)/8
        dy=(py-by)/8

        self.canvas.move(self.ball,dx,dy)

    # ------------------------------------------------

    def check_goal(self):

        bx,_,_,_=self.canvas.coords(self.ball)

        if bx < 5:

            if self.goal_callback:
                self.goal_callback("blue")

            self.reset_positions()

        if bx > 895:

            if self.goal_callback:
                self.goal_callback("red")

            self.reset_positions()

    # ------------------------------------------------

    def update_possession(self):

        if random.random()<0.5:
            self.possession["red"]+=1
        else:
            self.possession["blue"]+=1

        total=self.possession["red"]+self.possession["blue"]

        r=int(self.possession["red"]/total*100)
        b=100-r

        if self.possession_callback:
            self.possession_callback(r,b)

    # ------------------------------------------------

    def animate(self):

        if not self.running:
            return

        self.move_players()

        if random.random()<0.4:
            self.pass_ball()

        self.check_goal()

        self.update_possession()

        self.canvas.after(80,self.animate)

    # ------------------------------------------------

    def reset_positions(self):

        self.canvas.delete("all")
        self.players=[]

        self.draw_pitch()
        self.create_players()
        self.create_ball()