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

        self.animation_enabled = True

        self.build_ui()

    # -------------------------
    # UI
    # -------------------------

    def build_ui(self):

        title = tk.Label(
            self.root,
            text="Football Match Simulator",
            font=("Segoe UI", 26, "bold"),
            bg="#121212",
            fg="white"
        )
        title.pack(pady=15)

        self.build_controls()
        self.build_pitch()
        self.build_scoreboard()
        self.build_timeline()
        self.build_statusbar()

    # -------------------------
    # TEAM INPUT
    # -------------------------

    def build_controls(self):

        frame = tk.Frame(self.root, bg="#121212")
        frame.pack()

        tk.Label(frame, text="Home Team", fg="white", bg="#121212").grid(row=0, column=0)
        tk.Label(frame, text="Away Team", fg="white", bg="#121212").grid(row=1, column=0)

        self.team1_entry = tk.Entry(frame, width=20)
        self.team2_entry = tk.Entry(frame, width=20)

        self.team1_entry.grid(row=0, column=1, padx=5)
        self.team2_entry.grid(row=1, column=1, padx=5)

        self.sim_btn = tk.Button(
            frame,
            text="Simulate Match",
            command=self.simulate_match,
            bg="#1e88e5",
            fg="white"
        )

        self.sim_btn.grid(row=2, column=0, columnspan=2, pady=10)

        # extra buttons
        btn_frame = tk.Frame(self.root, bg="#121212")
        btn_frame.pack()

        tk.Button(
            btn_frame,
            text="Clear",
            width=12,
            command=self.clear_match
        ).grid(row=0, column=0, padx=5)

        tk.Button(
            btn_frame,
            text="Settings",
            width=12,
            command=self.open_settings
        ).grid(row=0, column=1, padx=5)

        tk.Button(
            btn_frame,
            text="Exit",
            width=12,
            command=self.confirm_exit
        ).grid(row=0, column=2, padx=5)

    # -------------------------
    # PITCH ANIMATION
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

        if self.animation_enabled:
            self.engine.animate()

    # -------------------------
    # SCOREBOARD
    # -------------------------

    def build_scoreboard(self):

        frame = tk.Frame(self.root, bg="#121212")
        frame.pack()

        self.score_label = tk.Label(
            frame,
            text="0 - 0",
            font=("Segoe UI", 36, "bold"),
            fg="#00e676",
            bg="#121212"
        )

        self.score_label.pack()

        self.stats_label = tk.Label(
            frame,
            text="Possession | Shots | xG",
            fg="white",
            bg="#121212"
        )

        self.stats_label.pack()

    # -------------------------
    # TIMELINE
    # -------------------------

    def build_timeline(self):

        title = tk.Label(
            self.root,
            text="Match Timeline",
            fg="white",
            bg="#121212",
            font=("Segoe UI", 14, "bold")
        )

        title.pack()

        frame = tk.Frame(self.root)
        frame.pack()

        scrollbar = tk.Scrollbar(frame)

        self.timeline = tk.Text(
            frame,
            height=12,
            width=100,
            bg="#1e1e1e",
            fg="white",
            yscrollcommand=scrollbar.set
        )

        scrollbar.config(command=self.timeline.yview)

        scrollbar.pack(side="right", fill="y")
        self.timeline.pack(side="left")

    # -------------------------
    # STATUS BAR
    # -------------------------

    def build_statusbar(self):

        self.status = tk.Label(
            self.root,
            text="Ready",
            anchor="w",
            bg="#1e1e1e",
            fg="white"
        )

        self.status.pack(fill="x", side="bottom")

    # -------------------------
    # MATCH
    # -------------------------

    def simulate_match(self):

        team1 = self.team1_entry.get().strip()
        team2 = self.team2_entry.get().strip()

        if not team1 or not team2:
            messagebox.showwarning("Input Error", "Enter both teams")
            return

        self.status.config(text="Simulating match...")

        try:

            result = run_match(team1, team2)

        except Exception as e:

            messagebox.showerror("Simulation Error", str(e))
            return

        score1, score2 = result["score"]

        self.score_label.config(text=f"{score1} - {score2}")

        pos1, pos2 = result["possession"]
        shots1, shots2 = result["stats"]["shots"]
        xg1, xg2 = result["stats"]["xg"]

        self.stats_label.config(
            text=f"Possession {pos1}-{pos2}% | Shots {shots1}-{shots2} | xG {round(xg1,2)}-{round(xg2,2)}"
        )

        self.timeline.delete(1.0, tk.END)

        for event in result["commentary"]:
            self.timeline.insert(tk.END, event + "\n")

        self.status.config(text="Match finished")

    # -------------------------
    # CLEAR
    # -------------------------

    def clear_match(self):

        self.score_label.config(text="0 - 0")
        self.timeline.delete(1.0, tk.END)
        self.stats_label.config(text="Possession | Shots | xG")
        self.status.config(text="Match cleared")

    # -------------------------
    # SETTINGS
    # -------------------------

    def open_settings(self):

        win = tk.Toplevel(self.root)

        win.title("Settings")
        win.geometry("300x250")

        tk.Label(win, text="Simulator Settings").pack(pady=10)

        toggle = tk.Button(
            win,
            text="Toggle Animation",
            command=self.toggle_animation
        )

        toggle.pack(pady=5)

        tk.Label(win, text="Future settings:").pack(pady=10)

        tk.Label(win, text="- Match speed").pack()
        tk.Label(win, text="- Difficulty").pack()
        tk.Label(win, text="- League database").pack()

    # -------------------------
    # TOGGLE ANIMATION
    # -------------------------

    def toggle_animation(self):

        self.animation_enabled = not self.animation_enabled

        if self.animation_enabled:
            self.engine.animate()
            self.status.config(text="Animation ON")

        else:
            self.status.config(text="Animation OFF")

    # -------------------------
    # EXIT
    # -------------------------

    def confirm_exit(self):

        if messagebox.askyesno("Exit", "Exit simulator?"):
            self.root.destroy()


# -------------------------
# START
# -------------------------

root = tk.Tk()

app = SoccerSimulator(root)

root.mainloop()