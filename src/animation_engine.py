from utils import resource_path

def play_match_animation():
    print(f"Playing match animation with assets from {resource_path('assets')}")
import pygame

pygame.init()

screen = pygame.display.set_mode((900,600))
pitch = pygame.image.load("assets/pitch.png")

running = True

while running:

    screen.blit(pitch,(0,0))

    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False

    pygame.display.update()
import random


class AnimationEngine:

    def __init__(self, canvas):

        self.canvas = canvas

        self.players = []
        self.ball = None

        self.create_players()
        self.create_ball()

    def create_players(self):

        # team 1
        for i in range(11):

            x = random.randint(100,400)
            y = random.randint(100,400)

            p = self.canvas.create_oval(
                x,y,x+15,y+15,
                fill="red"
            )

            self.players.append(p)

        # team 2
        for i in range(11):

            x = random.randint(500,800)
            y = random.randint(100,400)

            p = self.canvas.create_oval(
                x,y,x+15,y+15,
                fill="blue"
            )

            self.players.append(p)

    def create_ball(self):

        self.ball = self.canvas.create_oval(
            440,240,450,250,
            fill="white"
        )
    def move_players(self):

        for p in self.players:

            dx = random.randint(-5,5)
            dy = random.randint(-5,5)

            self.canvas.move(p,dx,dy)
    def move_ball(self):

        dx = random.randint(-8,8)
        dy = random.randint(-8,8)

        self.canvas.move(self.ball,dx,dy)
    def animate(self):

        self.move_players()
        self.move_ball()

        self.canvas.after(120,self.animate)