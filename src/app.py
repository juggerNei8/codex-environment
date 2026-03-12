import tkinter as tk
from tkinter import ttk
import pandas as pd
import os

from animation_engine import AnimationEngine
from match_engine import MatchEngine
from ball_physics import BallPhysics
from goalkeeper_ai import GoalKeeperAI
from audio_engine import AudioEngine
from logo_loader import LogoLoader


class FootballSimulator:

    def __init__(self, root):

        self.root = root
        self.root.title("Football Match Simulator")
        self.root.geometry("1400x720")
        self.root.configure(bg="#0f172a")

        # match state
        self.score_red = 0
        self.score_blue = 0
        self.match_time = 0

        # engines
        self.match_engine = MatchEngine()
        self.ball_physics = BallPhysics()
        self.gk_left = GoalKeeperAI("left")
        self.gk_right = GoalKeeperAI("right")
        self.audio = AudioEngine()
        self.logo_loader = LogoLoader()

        # database
        self.load_database()

        # UI
        self.build_ui()

        # animation
        self.engine = AnimationEngine(
            self.canvas,
            commentary_callback=self.add_commentary,
            goal_callback=self.goal_scored,
            possession_callback=self.update_possession
        )

        self.update_clock()

    # ------------------------------------------------
    # DATABASE
    # ------------------------------------------------

    def load_database(self):

        base_dir = os.path.dirname(os.path.abspath(__file__))
        teams_path = os.path.join(base_dir, "..", "database", "teams.csv")

        try:

            df = pd.read_csv(teams_path)

            if "team" in df.columns:
                self.team_list = sorted(df["team"].unique().tolist())
            else:
                self.team_list = sorted(df.iloc[:, 0].tolist())

            print("Teams loaded:", len(self.team_list))

        except:

            print("Database missing. Using fallback teams.")

            self.team_list = [
                "Team1","Team2","Team3","Team4","Team5","Team6"
            ]

    # ------------------------------------------------
    # UI
    # ------------------------------------------------

    def build_ui(self):

        header = tk.Frame(self.root, bg="#1e293b", height=80)
        header.pack(fill="x")

        self.score_label = tk.Label(
            header,
            text="0 - 0",
            font=("Arial",32,"bold"),
            bg="#1e293b",
            fg="white"
        )
        self.score_label.pack(side="left", padx=30)

        self.clock_label = tk.Label(
            header,
            text="00:00",
            font=("Arial",20),
            bg="#1e293b",
            fg="white"
        )
        self.clock_label.pack(side="right", padx=20)

        self.possession_label = tk.Label(
            header,
            text="Possession 50% - 50%",
            font=("Arial",12),
            bg="#1e293b",
            fg="white"
        )
        self.possession_label.pack(side="right", padx=20)

        main = tk.Frame(self.root, bg="#0f172a")
        main.pack(fill="both", expand=True)

        sidebar = tk.Frame(main, width=220, bg="#0b2545")
        sidebar.pack(side="left", fill="y")

        pitch_frame = tk.Frame(main, bg="#0f172a")
        pitch_frame.pack(side="left", expand=True)

        right_panel = tk.Frame(main, width=260, bg="#0b2545")
        right_panel.pack(side="right", fill="y")

        # -------------------
        # TEAM SELECTION
        # -------------------

        tk.Label(sidebar,text="HOME TEAM",bg="#0b2545",fg="white").pack(pady=10)

        self.home_box = ttk.Combobox(
            sidebar,
            values=self.team_list,
            height=20
        )
        self.home_box.pack()

        tk.Label(sidebar,text="AWAY TEAM",bg="#0b2545",fg="white").pack(pady=10)

        self.away_box = ttk.Combobox(
            sidebar,
            values=self.team_list,
            height=20
        )
        self.away_box.pack()

        if len(self.team_list) >= 2:
            self.home_box.current(0)
            self.away_box.current(1)

        # -------------------
        # BUTTONS
        # -------------------

        tk.Button(
            sidebar,
            text="Start Match",
            command=self.start_match,
            width=20
        ).pack(pady=15)

        tk.Button(
            sidebar,
            text="Pause",
            command=self.pause_match,
            width=20
        ).pack(pady=5)

        tk.Button(
            sidebar,
            text="Reset",
            command=self.reset_match,
            width=20
        ).pack(pady=5)

        # -------------------
        # PITCH
        # -------------------

        self.canvas = tk.Canvas(
            pitch_frame,
            width=900,
            height=500,
            bg="#2e7d32",
            highlightthickness=0
        )

        self.canvas.pack(expand=True,pady=30)

        # -------------------
        # LEAGUE TABLE
        # -------------------

        tk.Label(
            right_panel,
            text="League Table",
            bg="#0b2545",
            fg="white",
            font=("Arial",12,"bold")
        ).pack(pady=10)

        self.table_box = tk.Text(
            right_panel,
            height=15,
            width=30,
            bg="#091c34",
            fg="white"
        )
        self.table_box.pack()

        # -------------------
        # NEWS
        # -------------------

        tk.Label(
            right_panel,
            text="Club News",
            bg="#0b2545",
            fg="white",
            font=("Arial",12,"bold")
        ).pack(pady=10)

        self.news_box = tk.Text(
            right_panel,
            height=10,
            width=30,
            bg="#091c34",
            fg="white"
        )
        self.news_box.pack()

        # -------------------
        # COMMENTARY
        # -------------------

        self.commentary_box = tk.Text(
            self.root,
            height=6,
            bg="#020617",
            fg="white"
        )

        self.commentary_box.pack(fill="x")

    # ------------------------------------------------
    # MATCH CONTROL
    # ------------------------------------------------

    def start_match(self):

        if not self.engine.running:

            self.engine.running = True
            self.engine.animate()

            self.audio.play_crowd()

            home = self.home_box.get()
            away = self.away_box.get()

            self.add_commentary(f"{home} vs {away} kickoff!")

    def pause_match(self):

        self.engine.running = False
        self.add_commentary("Match paused.")

    def reset_match(self):

        self.engine.running = False
        self.engine.reset_positions()

        self.score_red = 0
        self.score_blue = 0
        self.match_time = 0

        self.clock_label.config(text="00:00")

        self.update_score()

        self.add_commentary("Match reset.")

    # ------------------------------------------------
    # EVENTS
    # ------------------------------------------------

    def goal_scored(self, team):

        if team == "red":
            self.score_red += 1
        else:
            self.score_blue += 1

        self.audio.play_goal()

        self.update_score()

        self.add_commentary(f"GOAL for {team.upper()}!")

    # ------------------------------------------------
    # UI
    # ------------------------------------------------

    def update_score(self):

        self.score_label.config(
            text=f"{self.score_red} - {self.score_blue}"
        )

    def update_possession(self, red, blue):

        self.possession_label.config(
            text=f"Possession {red}% - {blue}%"
        )

    def add_commentary(self, text):

        self.commentary_box.insert("end", text + "\n")

        lines = int(self.commentary_box.index('end-1c').split('.')[0])

        if lines > 120:
            self.commentary_box.delete("1.0","2.0")

        self.commentary_box.see("end")

    # ------------------------------------------------
    # CLOCK
    # ------------------------------------------------

    def update_clock(self):

        if self.engine.running:

            self.match_time += 1

            minutes = self.match_time // 60
            seconds = self.match_time % 60

            self.clock_label.config(
                text=f"{minutes:02}:{seconds:02}"
            )

        self.root.after(1000,self.update_clock)


# ------------------------------------------------

if __name__ == "__main__":

    root = tk.Tk()
    app = FootballSimulator(root)
    root.mainloop()