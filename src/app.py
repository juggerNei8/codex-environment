import os
import json
import tkinter as tk
from tkinter import ttk, messagebox
import pandas as pd

from animation_engine import AnimationEngine
from audio_engine import AudioEngine
from commentary_engine import CommentaryEngine
from live_data_hub import LiveDataHub
from season_engine import SeasonEngine
from transfer_market import TransferMarket


class JuggerNei8FootballSimulator:
    def __init__(self, root):
        self.root = root
        self.root.title("JuggerNei8 Football Simulator")
        self.root.geometry("1500x880")
        self.root.configure(bg="#0f172a")

        self.dark_mode = True

        self.home_score = 0
        self.away_score = 0
        self.match_time = 0

        self.audio = AudioEngine()
        self.commentary_engine = CommentaryEngine()
        self.live_data = LiveDataHub()
        self.season_engine = SeasonEngine()
        self.transfer_market = TransferMarket()

        self.team_list = []
        self.team_records = pd.DataFrame()
        self.load_database()

        self.build_ui()

        self.engine = AnimationEngine(
            self.canvas,
            commentary_callback=self.add_commentary,
            goal_callback=self.goal_scored,
            possession_callback=self.update_possession,
            stats_callback=self.update_stats
        )

        self.refresh_live_data_on_start()
        self.update_clock()

    # ------------------------------------------------
    # DATABASE
    # ------------------------------------------------

    def project_path(self, *parts):
        base_dir = os.path.dirname(os.path.abspath(__file__))
        return os.path.normpath(os.path.join(base_dir, "..", *parts))

    def ensure_database_files(self):
        db_dir = self.project_path("database")
        os.makedirs(db_dir, exist_ok=True)

        defaults = {
            "teams.csv": "team,league,country,strength\nArsenal,Premier League,England,85\nChelsea,Premier League,England,83\nBarcelona,La Liga,Spain,88\nReal Madrid,La Liga,Spain,90\n",
            "players.csv": "player,team,position,rating\nBukayo Saka,Arsenal,RW,87\nMartin Odegaard,Arsenal,CAM,88\nRobert Lewandowski,Barcelona,ST,89\nJude Bellingham,Real Madrid,CM,90\n",
            "fixtures.csv": "home,away,competition\nArsenal,Chelsea,League\nBarcelona,Real Madrid,League\n",
            "league_table.csv": "team,played,wins,draws,losses,gd,points\nArsenal,0,0,0,0,0,0\nChelsea,0,0,0,0,0,0\nBarcelona,0,0,0,0,0,0\nReal Madrid,0,0,0,0,0,0\n",
            "club_news.csv": "team,title,summary\nArsenal,Training report,Squad looks sharp ahead of kickoff.\nReal Madrid,Injury watch,Medical staff monitoring fitness.\n",
        }

        for filename, content in defaults.items():
            full = self.project_path("database", filename)
            if not os.path.exists(full):
                with open(full, "w", encoding="utf-8") as f:
                    f.write(content)

    def load_database(self):
        self.ensure_database_files()

        teams_path = self.project_path("database", "teams.csv")
        try:
            self.team_records = pd.read_csv(teams_path)

            if "team" not in self.team_records.columns:
                first_col = self.team_records.columns[0]
                self.team_records = self.team_records.rename(columns={first_col: "team"})

            self.team_list = sorted(self.team_records["team"].dropna().astype(str).unique().tolist())
            print("Teams loaded:", len(self.team_list))

        except Exception as e:
            print("Database not found or unreadable:", e)
            self.team_records = pd.DataFrame({"team": ["Team1", "Team2", "Team3", "Team4"]})
            self.team_list = ["Team1", "Team2", "Team3", "Team4"]

    # ------------------------------------------------
    # LIVE DATA
    # ------------------------------------------------

    def refresh_live_data_on_start(self):
        """
        Safe startup refresh:
        - if API keys are missing, simulator still runs
        - if internet fails, simulator still runs
        """
        try:
            result = self.live_data.refresh_all(self.project_path("database"))
            if result["updated"]:
                self.add_commentary("Live data refreshed.")
            else:
                self.add_commentary("Running with local database.")
        except Exception as e:
            self.add_commentary(f"Live refresh skipped: {e}")

        self.reload_side_panels()

    def reload_side_panels(self):
        self.table_box.delete("1.0", "end")
        self.news_box.delete("1.0", "end")

        table_path = self.project_path("database", "league_table.csv")
        news_path = self.project_path("database", "club_news.csv")

        try:
            table_df = pd.read_csv(table_path)
            for _, row in table_df.head(12).iterrows():
                self.table_box.insert(
                    "end",
                    f"{row.get('team','')}  P:{row.get('played',0)}  Pts:{row.get('points',0)}\n"
                )
        except Exception:
            self.table_box.insert("end", "League table unavailable.\n")

        try:
            news_df = pd.read_csv(news_path)
            for _, row in news_df.head(8).iterrows():
                self.news_box.insert(
                    "end",
                    f"{row.get('team','')}: {row.get('title','')}\n{row.get('summary','')}\n\n"
                )
        except Exception:
            self.news_box.insert("end", "Club news unavailable.\n")

    # ------------------------------------------------
    # UI
    # ------------------------------------------------

    def build_ui(self):
        self.main = tk.Frame(self.root, bg="#0f172a")
        self.main.pack(fill="both", expand=True)

        self.build_header()
        self.build_body()
        self.build_footer()

    def build_header(self):
        self.header = tk.Frame(self.main, bg="#1e293b", height=84)
        self.header.pack(fill="x")

        self.home_name_label = tk.Label(
            self.header, text="HOME", bg="#1e293b", fg="white",
            font=("Arial", 15, "bold")
        )
        self.home_name_label.pack(side="left", padx=18)

        self.score_label = tk.Label(
            self.header, text="0 - 0", bg="#1e293b", fg="white",
            font=("Arial", 36, "bold")
        )
        self.score_label.pack(side="left", padx=24)

        self.away_name_label = tk.Label(
            self.header, text="AWAY", bg="#1e293b", fg="white",
            font=("Arial", 15, "bold")
        )
        self.away_name_label.pack(side="left")

        self.clock_label = tk.Label(
            self.header, text="00:00", bg="#1e293b", fg="white",
            font=("Arial", 20)
        )
        self.clock_label.pack(side="right", padx=20)

        self.possession_label = tk.Label(
            self.header, text="Possession 50% - 50%", bg="#1e293b", fg="white",
            font=("Arial", 12)
        )
        self.possession_label.pack(side="right", padx=20)

    def build_body(self):
        body = tk.Frame(self.main, bg="#0f172a")
        body.pack(fill="both", expand=True)

        self.build_sidebar(body)
        self.build_pitch(body)
        self.build_right_panel(body)

    def build_sidebar(self, parent):
        self.sidebar = tk.Frame(parent, bg="#0b2545", width=290)
        self.sidebar.pack(side="left", fill="y")

        tk.Label(self.sidebar, text="Home Team", bg="#0b2545", fg="white").pack(pady=(16, 6))
        self.home_box = ttk.Combobox(self.sidebar, values=self.team_list, height=18, state="normal")
        self.home_box.pack(padx=12, fill="x")

        tk.Label(self.sidebar, text="Away Team", bg="#0b2545", fg="white").pack(pady=(16, 6))
        self.away_box = ttk.Combobox(self.sidebar, values=self.team_list, height=18, state="normal")
        self.away_box.pack(padx=12, fill="x")

        tk.Label(self.sidebar, text="Home Formation", bg="#0b2545", fg="white").pack(pady=(16, 6))
        self.home_formation_box = ttk.Combobox(self.sidebar, values=["4-3-3", "4-2-3-1"], state="readonly")
        self.home_formation_box.pack(padx=12, fill="x")

        tk.Label(self.sidebar, text="Away Formation", bg="#0b2545", fg="white").pack(pady=(16, 6))
        self.away_formation_box = ttk.Combobox(self.sidebar, values=["4-3-3", "4-2-3-1"], state="readonly")
        self.away_formation_box.pack(padx=12, fill="x")

        if len(self.team_list) >= 2:
            self.home_box.set(self.team_list[0])
            self.away_box.set(self.team_list[1])

        self.home_formation_box.set("4-3-3")
        self.away_formation_box.set("4-2-3-1")

        btn_cfg = {"width": 22, "bg": "#1b3a5a", "fg": "white", "activebackground": "#31577c"}

        tk.Button(self.sidebar, text="▶ Start Match", command=self.start_match, **btn_cfg).pack(pady=(20, 6))
        tk.Button(self.sidebar, text="⏸ Pause Match", command=self.pause_match, **btn_cfg).pack(pady=6)
        tk.Button(self.sidebar, text="🔄 Reset Match", command=self.reset_match, **btn_cfg).pack(pady=6)
        tk.Button(self.sidebar, text="📅 Season Mode", command=self.start_season_mode, **btn_cfg).pack(pady=6)
        tk.Button(self.sidebar, text="💰 Transfer Market", command=self.open_transfer_market, **btn_cfg).pack(pady=6)
        tk.Button(self.sidebar, text="⚙ Settings", command=self.open_settings, **btn_cfg).pack(pady=6)
        tk.Button(self.sidebar, text="❌ Quit", command=self.quit_app, **btn_cfg).pack(pady=6)

    def build_pitch(self, parent):
        self.pitch_wrap = tk.Frame(parent, bg="#0f172a")
        self.pitch_wrap.pack(side="left", fill="both", expand=True)

        self.canvas = tk.Canvas(
            self.pitch_wrap,
            width=900,
            height=500,
            bg="#2e7d32",
            highlightthickness=0
        )
        self.canvas.pack(expand=True, pady=26)

    def build_right_panel(self, parent):
        self.right_panel = tk.Frame(parent, bg="#0b2545", width=310)
        self.right_panel.pack(side="right", fill="y")

        tk.Label(self.right_panel, text="Match Statistics", bg="#0b2545", fg="white", font=("Arial", 12, "bold")).pack(pady=10)

        self.stats_box = tk.Text(self.right_panel, height=14, width=35, bg="#091c34", fg="white")
        self.stats_box.pack(padx=10)

        tk.Label(self.right_panel, text="League Table", bg="#0b2545", fg="white", font=("Arial", 12, "bold")).pack(pady=10)

        self.table_box = tk.Text(self.right_panel, height=12, width=35, bg="#091c34", fg="white")
        self.table_box.pack(padx=10)

        tk.Label(self.right_panel, text="Club News", bg="#0b2545", fg="white", font=("Arial", 12, "bold")).pack(pady=10)

        self.news_box = tk.Text(self.right_panel, height=8, width=35, bg="#091c34", fg="white")
        self.news_box.pack(padx=10)

    def build_footer(self):
        self.commentary_box = tk.Text(self.root, height=7, bg="#020617", fg="white")
        self.commentary_box.pack(fill="x")

    # ------------------------------------------------
    # MATCH CONTROL
    # ------------------------------------------------

    def start_match(self):
        home = self.home_box.get().strip()
        away = self.away_box.get().strip()
        home_form = self.home_formation_box.get().strip()
        away_form = self.away_formation_box.get().strip()

        if not home or not away:
            self.add_commentary("Please select both teams.")
            return

        self.home_name_label.config(text=home)
        self.away_name_label.config(text=away)

        self.engine.configure_match(home, away, home_form, away_form)

        if not self.engine.running:
            self.engine.running = True
            self.engine.animate()
            self.audio.play_crowd()
            self.add_commentary(f"{home} vs {away} kickoff!")

    def pause_match(self):
        self.engine.running = False
        self.add_commentary("Match paused.")

    def reset_match(self):
        self.engine.reset_match()
        self.engine.running = False

        self.home_score = 0
        self.away_score = 0
        self.match_time = 0

        self.clock_label.config(text="00:00")
        self.score_label.config(text="0 - 0")
        self.possession_label.config(text="Possession 50% - 50%")
        self.stats_box.delete("1.0", "end")

        self.add_commentary("Match reset.")

    def start_season_mode(self):
        teams = self.team_list[:10] if len(self.team_list) >= 10 else self.team_list
        self.season_engine.load_teams(teams)
        self.season_engine.generate_fixtures()
        self.add_commentary(f"Season mode started with {len(teams)} teams.")
        self.reload_side_panels()

    def open_transfer_market(self):
        self.transfer_market.generate_mock_market(self.team_list[:20])
        win = tk.Toplevel(self.root)
        win.title("Transfer Market")
        win.geometry("520x420")

        box = tk.Text(win, bg="#091c34", fg="white")
        box.pack(fill="both", expand=True)

        for item in self.transfer_market.market[:30]:
            box.insert(
                "end",
                f"{item['player']} | {item['team']} | {item['position']} | Value: {item['value']}m\n"
            )

    # ------------------------------------------------
    # EVENTS / UI UPDATES
    # ------------------------------------------------

    def goal_scored(self, team):
        if team == "home":
            self.home_score += 1
        else:
            self.away_score += 1

        self.audio.play_goal()
        self.score_label.config(text=f"{self.home_score} - {self.away_score}")
        self.add_commentary(self.commentary_engine.goal_commentary())

    def update_possession(self, home, away):
        self.possession_label.config(text=f"Possession {home}% - {away}%")

    def update_stats(self, stats):
        self.stats_box.delete("1.0", "end")
        self.stats_box.insert("end", f"Home Shots: {stats['home_shots']}\n")
        self.stats_box.insert("end", f"Away Shots: {stats['away_shots']}\n")
        self.stats_box.insert("end", f"Home On Target: {stats['home_on_target']}\n")
        self.stats_box.insert("end", f"Away On Target: {stats['away_on_target']}\n")
        self.stats_box.insert("end", f"Home Passes: {stats['home_passes']}\n")
        self.stats_box.insert("end", f"Away Passes: {stats['away_passes']}\n")
        self.stats_box.insert("end", f"Home Saves: {stats['home_saves']}\n")
        self.stats_box.insert("end", f"Away Saves: {stats['away_saves']}\n")

    def add_commentary(self, text):
        self.commentary_box.insert("end", text + "\n")
        lines = int(self.commentary_box.index("end-1c").split(".")[0])
        if lines > 160:
            self.commentary_box.delete("1.0", "2.0")
        self.commentary_box.see("end")

    # ------------------------------------------------
    # CLOCK
    # ------------------------------------------------

    def update_clock(self):
        if hasattr(self, "engine") and self.engine.running:
            self.match_time += 1
            minutes = self.match_time // 60
            seconds = self.match_time % 60
            self.clock_label.config(text=f"{minutes:02}:{seconds:02}")

        self.root.after(1000, self.update_clock)

    # ------------------------------------------------
    # SETTINGS / QUIT
    # ------------------------------------------------

    def open_settings(self):
        win = tk.Toplevel(self.root)
        win.title("Settings")
        win.geometry("340x240")

        tk.Label(win, text="Appearance", font=("Arial", 12, "bold")).pack(pady=10)
        tk.Button(win, text="Toggle Dark / Light", command=self.toggle_theme).pack(pady=6)
        tk.Button(win, text="Mute / Unmute Crowd", command=self.toggle_mute).pack(pady=6)

    def toggle_theme(self):
        self.dark_mode = not self.dark_mode
        if self.dark_mode:
            self.root.configure(bg="#0f172a")
        else:
            self.root.configure(bg="#dbe4ee")

    def toggle_mute(self):
        self.audio.set_muted(not self.audio.muted)

    def quit_app(self):
        if messagebox.askyesno("Quit", "Exit simulator?"):
            self.root.destroy()


if __name__ == "__main__":
    root = tk.Tk()
    app = JuggerNei8FootballSimulator(root)
    root.mainloop()