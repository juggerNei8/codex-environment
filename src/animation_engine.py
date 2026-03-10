import tkinter as tk
import random

def animate(canvas):

    ball = canvas.create_oval(380,230,400,250,fill="white")

    for i in range(50):

        dx = random.randint(-10,10)
        dy = random.randint(-10,10)

        canvas.move(ball,dx,dy)
        canvas.update()
        canvas.after(100)