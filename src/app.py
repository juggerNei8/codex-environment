import tkinter as tk
from tkinter import ttk, messagebox
import pandas as pd
import os

from animation_engine import AnimationEngine
from audio_engine import AudioEngine
from commentary_engine import CommentaryEngine
from live_data_hub import LiveDataHub
from player_database import PlayerDatabase
from prediction_engine import PredictionEngine
from manager_ai import ManagerAI
from transfer_market import TransferMarket
from logo_loader import LogoLoader


class FootballSimulator:
    def __init__(self, root):
        self.root = root
        self.root.title("Football Match Simulator")
        self.root.geometry("1500x920")
        self.root.configure(bg="#0f172a")

        self.dark_mode = True
        self.match_duration_seconds = 8
        self.live_refresh_ms = 10 * 60 * 1000  # 10 minutes

        self.home_score = 0
        self.away_score = 0
        self.match_time = 0
        self.match_finished = False

        self.audio = AudioEngine()
        self.commentary_engine = CommentaryEngine()
        self.live_data = LiveDataHub()
        self.player_db = PlayerDatabase()
        self.prediction_engine = PredictionEngine()
        self.manager_ai = ManagerAI()
        self.transfer_market = TransferMarket()
        self.logo_loader = LogoLoader()

        self.team_list = []
        self.teams_df = pd.DataFrame()
        self.players_df = pd.DataFrame()
        self.team_form_df = pd.DataFrame()

        self.load_database()
        self.build_ui()

        self.engine = AnimationEngine(
            self.canvas,
            commentary_callback=self.add_commentary,
            goal_callback=self.goal_scored,
            possession_callback=self.update_possession,
            stats_callback=self.update_stats
        )

        self.refresh_live_data()
        self.update_clock()
        self.update_manager_tactics_loop()
        self.schedule_live_refresh_loop()

    # ------------------------------------------------
    # PATHS
    # ------------------------------------------------

    def project_path(self, *parts):
        base_dir = os.path.dirname(os.path.abspath(__file__))
        return os.path.normpath(os.path.join(base_dir, "..", *parts))

    # ------------------------------------------------
    # DATABASE
    # ------------------------------------------------

    def ensure_database_files(self):
        db_dir = self.project_path("database")
        os.makedirs(db_dir, exist_ok=True)

        defaults = {
            "teams.csv": "team,league,country,strength\nArsenal,Premier League,England,85\nChelsea,Premier League,England,83\nBarcelona,La Liga,Spain,88\nReal Madrid,La Liga,Spain,90\n",
            "players.csv": "player,team,position,rating\nBukayo Saka,Arsenal,RW,87\nMartin Odegaard,Arsenal,CAM,88\nCole Palmer,Chelsea,CAM,86\nJude Bellingham,Real Madrid,CM,90\n",
            "fixtures.csv": "home,away,competition,utcDate,status\nArsenal,Chelsea,League,,SCHEDULED\nBarcelona,Real Madrid,League,,SCHEDULED\n",
            "league_table.csv": "team,played,wins,draws,losses,gd,points\nArsenal,0,0,0,0,0,0\nChelsea,0,0,0,0,0,0\nBarcelona,0,0,0,0,0,0\nReal Madrid,0,0,0,0,0,0\n",
            "club_news.csv": "team,title,summary\nGeneral,Startup,Simulator started with local data.\n",
            "team_form.csv": "team,form_last5,injuries_count,cards_pressure,morale\nArsenal,0.62,0,0.15,0.68\nChelsea,0.58,1,0.18,0.64\nBarcelona,0.66,0,0.14,0.72\nReal Madrid,0.69,0,0.12,0.75\n",
        }

        for filename, content in defaults.items():
            full = self.project_path("database", filename)
            if not os.path.exists(full) or os.path.getsize(full) == 0:
                with open(full, "w", encoding="utf-8") as f:
                    f.write(content)

    def load_database(self):
        self.ensure_database_files()

        teams_path = self.project_path("database", "teams.csv")
        self.teams_df = pd.read_csv(teams_path)

        if "team" not in self.teams_df.columns:
            first_col = self.teams_df.columns[0]
            self.teams_df = self.teams_df.rename(columns={first_col: "team"})

        self.team_list = sorted(self.teams_df["team"].dropna().astype(str).unique().tolist())
        print("Teams loaded:", len(self.team_list))

        self.players_df = self.player_db.load_or_enrich(self.project_path("database"))

        form_path = self.project_path("database", "team_form.csv")
        if os.path.exists(form_path) and os.path.getsize(form_path) > 0:
            try:
                self.team_form_df = pd.read_csv(form_path)
            except Exception:
                self.team_form_df = pd.DataFrame()

    # ------------------------------------------------
    # LIVE REFRESH
    # ------------------------------------------------

    def refresh_live_data(self):
        db_dir = self.project_path("database")

        result = self.live_data.refresh_all(db_dir, competition_code="PL")
        self.live_data.ensure_players_exists(db_dir)

        self.load_database()
        self.reload_selectors()
        self.reload_side_panels()

        self.transfer_market.build_from_players(self.players_df)
        self.transfer_market.save_to_csv(db_dir)

        if result["updated"]:
            self.add_commentary("Live football data refreshed.")
        else:
            self.add_commentary("Running with local database.")

        for note in result["notes"]:
            self.add_commentary(note)

    def schedule_live_refresh_loop(self):
        self.refresh_live_data()
        self.root.after(self.live_refresh_ms, self.schedule_live_refresh_loop)

    def reload_selectors(self):
        self.home_box["values"] = self.team_list
        self.away_box["values"] = self.team_list

        if len(self.team_list) >= 2:
            if not self.home_box.get():
                self.home_box.set(self.team_list[0])
            if not self.away_box.get():
                self.away_box.set(self.team_list[1])

    def reload_side_panels(self):
        self.table_box.delete("1.0", "end")
        self.fixtures_box.delete("1.0", "end")
        self.news_box.delete("1.0", "end")

        try:
            table_df = pd.read_csv(self.project_path("database", "league_table.csv"))
            for _, row in table_df.head(16).iterrows():
                self.table_box.insert("end", f"{row.get('team','')}  P:{row.get('played',0)}  Pts:{row.get('points',0)}\n")
        except Exception:
            self.table_box.insert("end", "League table unavailable.\n")

        try:
            fix_df = pd.read_csv(self.project_path("database", "fixtures.csv"))
            for _, row in fix_df.head(14).iterrows():
                self.fixtures_box.insert("end", f"{row.get('home','')} vs {row.get('away','')}  {row.get('status','')}\n")
        except Exception:
            self.fixtures_box.insert("end", "Fixtures unavailable.\n")

        try:
            news_df = pd.read_csv(self.project_path("database", "club_news.csv"))
            for _, row in news_df.head(10).iterrows():
                self.news_box.insert("end", f"{row.get('title','')}\n{row.get('summary','')}\n\n")
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

        self.home_logo_label = tk.Label(self.header, bg="#1e293b")
        self.home_logo_label.pack(side="left", padx=(12, 4))

        self.home_name_label = tk.Label(self.header, text="HOME", bg="#1e293b", fg="white", font=("Arial", 15, "bold"))
        self.home_name_label.pack(side="left", padx=8)

        self.score_label = tk.Label(self.header, text="0 - 0", bg="#1e293b", fg="white", font=("Arial", 36, "bold"))
        self.score_label.pack(side="left", padx=24)

        self.away_name_label = tk.Label(self.header, text="AWAY", bg="#1e293b", fg="white", font=("Arial", 15, "bold"))
        self.away_name_label.pack(side="left", padx=8)

        self.away_logo_label = tk.Label(self.header, bg="#1e293b")
        self.away_logo_label.pack(side="left", padx=(4, 12))

        self.clock_label = tk.Label(self.header, text="00:00", bg="#1e293b", fg="white", font=("Arial", 20))
        self.clock_label.pack(side="right", padx=20)

        self.possession_label = tk.Label(self.header, text="Possession 50% - 50%", bg="#1e293b", fg="white", font=("Arial", 12))
        self.possession_label.pack(side="right", padx=20)

    def build_body(self):
        body = tk.Frame(self.main, bg="#0f172a")
        body.pack(fill="both", expand=True)

        self.build_sidebar(body)
        self.build_pitch(body)
        self.build_right_panel(body)

    def build_sidebar(self, parent):
        self.sidebar = tk.Frame(parent, bg="#0b2545", width=300)
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
        tk.Button(self.sidebar, text="🔃 Refresh Live Data", command=self.refresh_live_data, **btn_cfg).pack(pady=6)
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
        self.right_panel = tk.Frame(parent, bg="#0b2545", width=350)
        self.right_panel.pack(side="right", fill="y")

        tk.Label(self.right_panel, text="Match Statistics", bg="#0b2545", fg="white", font=("Arial", 12, "bold")).pack(pady=10)
        self.stats_box = tk.Text(self.right_panel, height=10, width=40, bg="#091c34", fg="white")
        self.stats_box.pack(padx=10)

        tk.Label(self.right_panel, text="League Table", bg="#0b2545", fg="white", font=("Arial", 12, "bold")).pack(pady=10)
        self.table_box = tk.Text(self.right_panel, height=9, width=40, bg="#091c34", fg="white")
        self.table_box.pack(padx=10)

        tk.Label(self.right_panel, text="Fixtures", bg="#0b2545", fg="white", font=("Arial", 12, "bold")).pack(pady=10)
        self.fixtures_box = tk.Text(self.right_panel, height=7, width=40, bg="#091c34", fg="white")
        self.fixtures_box.pack(padx=10)

        tk.Label(self.right_panel, text="Club News", bg="#0b2545", fg="white", font=("Arial", 12, "bold")).pack(pady=10)
        self.news_box = tk.Text(self.right_panel, height=7, width=40, bg="#091c34", fg="white")
        self.news_box.pack(padx=10)

    def build_footer(self):
        self.commentary_box = tk.Text(self.root, height=8, bg="#020617", fg="white")
        self.commentary_box.pack(fill="x")

    # ------------------------------------------------
    # MATCH CONTROL
    # ------------------------------------------------

    def get_team_strength(self, team_name):
        try:
            row = self.teams_df[self.teams_df["team"] == team_name].iloc[0]
            return float(row.get("strength", 75))
        except Exception:
            return 75.0

    def get_form_row(self, team_name):
        if self.team_form_df is None or self.team_form_df.empty:
            return None
        rows = self.team_form_df[self.team_form_df["team"] == team_name]
        if rows.empty:
            return None
        return rows.iloc[0]

    def get_team_form(self, team_name):
        row = self.get_form_row(team_name)
        return float(row["form_last5"]) if row is not None and "form_last5" in row else 0.60

    def get_team_morale(self, team_name):
        row = self.get_form_row(team_name)
        return float(row["morale"]) if row is not None and "morale" in row else 0.65

    def load_header_logos(self, home, away):
        home_logo = self.logo_loader.load(home)
        away_logo = self.logo_loader.load(away)

        if home_logo is not None:
            self.home_logo_label.config(image=home_logo)
            self.home_logo_label.image = home_logo

        if away_logo is not None:
            self.away_logo_label.config(image=away_logo)
            self.away_logo_label.image = away_logo

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
        self.load_header_logos(home, away)

        prediction = self.prediction_engine.predict_match(
            self.get_team_strength(home),
            self.get_team_strength(away),
            self.get_team_form(home),
            self.get_team_form(away),
            self.get_team_morale(home),
            self.get_team_morale(away),
        )
        self.add_commentary(self.prediction_engine.format_prediction(home, away, prediction))

        self.engine.configure_match(home, away, home_form, away_form)

        self.home_score = 0
        self.away_score = 0
        self.match_time = 0
        self.match_finished = False
        self.score_label.config(text="0 - 0")
        self.clock_label.config(text="00:00")

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
        self.match_finished = False

        self.clock_label.config(text="00:00")
        self.score_label.config(text="0 - 0")
        self.possession_label.config(text="Possession 50% - 50%")
        self.stats_box.delete("1.0", "end")

        self.add_commentary("Match reset.")

    def open_transfer_market(self):
        db_dir = self.project_path("database")
        self.transfer_market.load_from_csv(db_dir)

        win = tk.Toplevel(self.root)
        win.title("Transfer Market")
        win.geometry("540x430")

        box = tk.Text(win, bg="#091c34", fg="white")
        box.pack(fill="both", expand=True)

        if self.transfer_market.market.empty:
            box.insert("end", "No market data available.\n")
            return

        for _, row in self.transfer_market.market.head(40).iterrows():
            box.insert(
                "end",
                f"{row.get('player','')} | {row.get('team','')} | {row.get('position','')} | "
                f"Rating {row.get('rating','')} | Value {row.get('value','')}m\n"
            )

    # ------------------------------------------------
    # LIVE TACTICS
    # ------------------------------------------------

    def update_manager_tactics_loop(self):
        if hasattr(self, "engine") and self.engine.running and not self.match_finished:
            home_pos, away_pos = self.engine.get_possession_snapshot()

            home_decision = self.manager_ai.decide(
                "home",
                self.home_score,
                self.away_score,
                self.engine.get_average_stamina("home"),
                home_pos
            )
            away_decision = self.manager_ai.decide(
                "away",
                self.away_score,
                self.home_score,
                self.engine.get_average_stamina("away"),
                away_pos
            )

            self.engine.set_tactics(home_decision, away_decision)

        self.root.after(2000, self.update_manager_tactics_loop)

    # ------------------------------------------------
    # UI UPDATES
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
        if lines > 200:
            self.commentary_box.delete("1.0", "2.0")
        self.commentary_box.see("end")

    # ------------------------------------------------
    # CLOCK / MATCH END
    # ------------------------------------------------

    def finish_match(self):
        if self.match_finished:
            return

        self.match_finished = True
        self.engine.running = False

        home = self.home_box.get().strip()
        away = self.away_box.get().strip()

        self.add_commentary(f"Full time: {home} {self.home_score} - {self.away_score} {away}")

        pred = self.prediction_engine.predict_match(
            self.get_team_strength(home),
            self.get_team_strength(away),
            self.get_team_form(home),
            self.get_team_form(away),
            self.get_team_morale(home),
            self.get_team_morale(away),
        )
        self.add_commentary("Prediction reference after result:")
        self.add_commentary(self.prediction_engine.format_prediction(home, away, pred))

    def update_clock(self):
        if hasattr(self, "engine") and self.engine.running and not self.match_finished:
            self.match_time += 1
            minutes = self.match_time // 60
            seconds = self.match_time % 60
            self.clock_label.config(text=f"{minutes:02}:{seconds:02}")

            if self.match_time >= self.match_duration_seconds:
                self.finish_match()

        self.root.after(1000, self.update_clock)

    # ------------------------------------------------
    # SETTINGS / QUIT
    # ------------------------------------------------

    def open_settings(self):
        win = tk.Toplevel(self.root)
        win.title("Settings")
        win.geometry("380x300")

        tk.Label(win, text="Appearance", font=("Arial", 12, "bold")).pack(pady=10)
        tk.Button(win, text="Toggle Dark / Light", command=self.toggle_theme).pack(pady=6)
        tk.Button(win, text="Mute / Unmute Crowd", command=self.toggle_mute).pack(pady=6)

        tk.Label(win, text="Simulation", font=("Arial", 12, "bold")).pack(pady=10)
        tk.Button(win, text="Set Match Length = 5s", command=lambda: self.set_match_duration(5)).pack(pady=4)
        tk.Button(win, text="Set Match Length = 8s", command=lambda: self.set_match_duration(8)).pack(pady=4)
        tk.Button(win, text="Set Live Refresh = 10 min", command=lambda: self.set_live_refresh(10)).pack(pady=4)
        tk.Button(win, text="Set Live Refresh = 15 min", command=lambda: self.set_live_refresh(15)).pack(pady=4)

    def set_match_duration(self, secs):
        self.match_duration_seconds = secs
        self.add_commentary(f"Match duration set to {secs} seconds.")

    def set_live_refresh(self, mins):
        self.live_refresh_ms = mins * 60 * 1000
        self.add_commentary(f"Live data refresh set to every {mins} minutes.")

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
    app = FootballSimulator(root)
    root.mainloop()