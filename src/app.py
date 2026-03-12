import tkinter as tk
from tkinter import messagebox
from match_engine import run_match
from animation_engine import AnimationEngine

WINDOW_WIDTH = 1200
WINDOW_HEIGHT = 800


class SoccerSimulator:

    def __init__(self, root):

        self.root = root
        self.root.title("Football Match Simulator")

        self.root.geometry(f"{WINDOW_WIDTH}x{WINDOW_HEIGHT}")
        self.root.configure(bg="#121212")

        self.root.protocol("WM_DELETE_WINDOW", self.confirm_exit)

        self.minute = 0
        self.running_clock = False

        self.build_ui()

    # -------------------------
    # UI
    # -------------------------

    def build_ui(self):

        title = tk.Label(
            self.root,
            text="Football Match Simulator",
            font=("Segoe UI",26,"bold"),
            bg="#121212",
            fg="white"
        )
        title.pack(pady=15)

        self.build_controls()
        self.build_pitch()
        self.build_scoreboard()
        self.build_clock()

    # -------------------------
    # TEAM INPUT
    # -------------------------

    def build_controls(self):

        frame = tk.Frame(self.root,bg="#121212")
        frame.pack()

        tk.Label(frame,text="Home Team",fg="white",bg="#121212").grid(row=0,column=0)
        tk.Label(frame,text="Away Team",fg="white",bg="#121212").grid(row=1,column=0)

        self.team1_entry = tk.Entry(frame,width=20)
        self.team2_entry = tk.Entry(frame,width=20)

        self.team1_entry.grid(row=0,column=1)
        self.team2_entry.grid(row=1,column=1)

        tk.Button(
            frame,
            text="Simulate Match",
            command=self.simulate_match,
            bg="#1e88e5",
            fg="white"
        ).grid(row=2,column=0,columnspan=2,pady=10)

    # -------------------------
    # PITCH
    # -------------------------

    def build_pitch(self):

        self.pitch = tk.Canvas(
            self.root,
            width=900,
            height=500,
            bg="green",
            highlightthickness=0
        )

        self.pitch.pack(pady=10)

        self.engine = AnimationEngine(self.pitch)
        self.engine.animate()

    # -------------------------
    # SCOREBOARD
    # -------------------------

    def build_scoreboard(self):

        self.score_label = tk.Label(
            self.root,
            text="0 - 0",
            font=("Segoe UI",36,"bold"),
            fg="#00e676",
            bg="#121212"
        )

        self.score_label.pack()

    # -------------------------
    # MATCH CLOCK
    # -------------------------

    def build_clock(self):

        self.clock = tk.Label(
            self.root,
            text="0'",
            font=("Segoe UI",18),
            fg="white",
            bg="#121212"
        )

        self.clock.pack()

    def update_clock(self):

        if not self.running_clock:
            return

        self.minute += 1
        self.clock.config(text=f"{self.minute}'")

        if self.minute < 90:
            self.root.after(1000,self.update_clock)

    # -------------------------
    # MATCH
    # -------------------------

    def simulate_match(self):

        team1 = self.team1_entry.get().strip()
        team2 = self.team2_entry.get().strip()

        if not team1 or not team2:
            messagebox.showwarning("Input Error","Enter both teams")
            return

        result = run_match(team1,team2)

        s1,s2 = result["score"]

        self.score_label.config(text=f"{s1} - {s2}")

        self.minute = 0
        self.running_clock = True
        self.update_clock()

    # -------------------------
    # EXIT
    # -------------------------

    def confirm_exit(self):

        if messagebox.askyesno("Exit","Exit simulator?"):
            self.root.destroy()


root = tk.Tk()

app = SoccerSimulator(root)

root.mainloop()