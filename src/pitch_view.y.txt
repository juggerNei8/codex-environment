import customtkinter as ctk


class PitchView:

    def __init__(self, root):

        self.canvas = ctk.CTkCanvas(root, width=900, height=500, bg="green")
        self.canvas.pack(pady=10)

        self.draw_pitch()

    def draw_pitch(self):

        c = self.canvas

        # outer boundary
        c.create_rectangle(50,50,850,450, outline="white", width=3)

        # center line
        c.create_line(450,50,450,450, fill="white", width=3)

        # center circle
        c.create_oval(400,200,500,300, outline="white", width=3)

        # left penalty box
        c.create_rectangle(50,150,200,350, outline="white", width=3)

        # right penalty box
        c.create_rectangle(700,150,850,350, outline="white", width=3)

        # goals
        c.create_rectangle(30,220,50,280, outline="white", width=3)
        c.create_rectangle(850,220,870,280, outline="white", width=3)