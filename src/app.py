from __future__ import annotations

import os
import random
import tkinter as tk
from tkinter import ttk, messagebox, filedialog

os.environ.setdefault("SIMULATOR_TOKEN", "change_me_simulator_token")
os.environ.setdefault("BACKEND_BASE_URL", "http://127.0.0.1:8001")
os.environ.setdefault("ENABLE_HTTP_FALLBACK", "true")
os.environ.setdefault("CACHE_DIR", r"C:\Project X\football-gateway\cache")

from animation_engine import AnimationEngine
from audio_engine import AudioEngine
from commentary_engine import CommentaryEngine
from transfer_market import TransferMarket
from logo_loader import LogoLoader
from timeline_engine import TimelineEngine
from backend_launcher import BackendLauncher
from prediction_engine import PredictionEngine
from logging_helper import get_logger

from sim_integration.backend_client import SimulatorDataClient
from sim_integration.tk_helpers import run_in_background


logger = get_logger("simulator_app", "simulator_app.log")

APP_VERSION = "v1.4.1"
APP_COPYRIGHT = "© 2026 JuggerNei8 Football Simulator"

LEAGUE_OPTIONS = {
    "Premier League": "PL",
    "La Liga": "PD",
    "Bundesliga": "BL1",
    "Serie A": "SA",
    "Ligue 1": "FL1",
    "Champions League": "CL",
    "Europa League": "EL",
    "Conference League": "UCL",
    "Eredivisie": "DED",
    "Primeira Liga": "PPL",
}

FONT_FAMILIES = [
    "Arial",
    "Calibri",
    "Verdana",
    "Tahoma",
    "Trebuchet MS",
    "Georgia",
    "Times New Roman",
    "Courier New",
]

THEME_PRESETS = {
    "Night Blue": {
        "theme_bg": "#0b1020",
        "card_bg": "#12182b",
        "panel_bg": "#1a2137",
        "text_fg": "#f8fafc",
        "muted_fg": "#9aa9c3",
        "accent": "#c026d3",
        "accent2": "#60a5fa",
        "pitch_bg": "#1f6f43",
    },
    "Broadcast Purple": {
        "theme_bg": "#0a0817",
        "card_bg": "#161327",
        "panel_bg": "#201a37",
        "text_fg": "#f8fafc",
        "muted_fg": "#b4b2ca",
        "accent": "#a855f7",
        "accent2": "#38bdf8",
        "pitch_bg": "#1d6d46",
    },
    "Slate Light": {
        "theme_bg": "#dbe4ee",
        "card_bg": "#f8fafc",
        "panel_bg": "#cbd5e1",
        "text_fg": "#0f172a",
        "muted_fg": "#475569",
        "accent": "#7c3aed",
        "accent2": "#2563eb",
        "pitch_bg": "#2e7d32",
    },
}


class FootballSimulator:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("JuggerNei8 Football Simulator")
        try:
            self.root.state("zoomed")
        except Exception:
            self.root.geometry("1500x900")
        self.root.minsize(1280, 760)

        self.current_competition = os.getenv("DEFAULT_COMPETITION", "PL")
        self.live_refresh_ms = 5 * 60 * 1000
        self.match_duration_seconds = 60
        self.fast_graphics = False
        self.audio_enabled = True
        self.backend_online = False
        self.last_data_source = "unknown"
        self.current_page = "live_match"
        self.panel_filter = ""

        self.font_family = "Arial"
        self.header_font_size = 16
        self.body_font_size = 10
        self.score_font_size = 28

        theme = THEME_PRESETS["Broadcast Purple"]
        self.theme_bg = theme["theme_bg"]
        self.card_bg = theme["card_bg"]
        self.panel_bg = theme["panel_bg"]
        self.text_fg = theme["text_fg"]
        self.muted_fg = theme["muted_fg"]
        self.accent = theme["accent"]
        self.accent2 = theme["accent2"]
        self.pitch_bg = theme["pitch_bg"]

        self.main_background_path = ""
        self.general_background_path = ""
        self.pitch_background_path = ""
        self.stadium_background_path = ""

        self.home_score = 0
        self.away_score = 0
        self.match_time = 0
        self.match_finished = False

        self.audio = AudioEngine()
        self.commentary_engine = CommentaryEngine()
        self.transfer_market = TransferMarket()
        self.logo_loader = LogoLoader()
        self.timeline_engine = TimelineEngine()
        self.backend_launcher = BackendLauncher()
        self.prediction_engine = PredictionEngine()
        self.data_client = SimulatorDataClient()

        self.team_list = []
        self.teams = []
        self.fixtures = []
        self.standings = []
        self.news_items = []
        self.live_games = {}
        self.odds_markets = {}
        self.bet365_prematch = {}
        self.tournament_odds = {}
        self.selected_fixture_odds = {}
        self.home_form_data = {}
        self.away_form_data = {}
        self.export_status = {}
        self.backend_usage = {}

        self.home_sidebar_badge_img = None
        self.away_sidebar_badge_img = None
        self.detail_home_badge_img = None
        self.detail_away_badge_img = None

        self.build_ui()

        self.engine = AnimationEngine(
            self.canvas,
            commentary_callback=self.add_commentary,
            goal_callback=self.goal_scored,
            possession_callback=self.update_possession,
            stats_callback=self.update_stats,
            timeline_callback=self.add_timeline_event,
        )
        self.engine.frame_ms = 12

        self.startup_backend_then_load()
        self.update_clock()
        self.update_manager_tactics_loop()
        self.schedule_live_refresh_loop()

    # ------------------------------------------------
    # UI SHELL
    # ------------------------------------------------

    def build_ui(self):
        self.root.configure(bg=self.theme_bg)

        self.main = tk.Frame(self.root, bg=self.theme_bg)
        self.main.pack(fill="both", expand=True)

        self.build_top_shell()
        self.build_header_strip()
        self.build_page_host()
        self.build_pages()
        self.apply_theme_to_widgets()
        self.show_page("live_match")

    def build_top_shell(self):
        self.top_shell = tk.Frame(self.main, bg="#0a0f1d", height=56)
        self.top_shell.pack(fill="x")
        self.top_shell.pack_propagate(False)

        left = tk.Frame(self.top_shell, bg="#0a0f1d")
        left.pack(side="left", fill="y", padx=8)

        mid = tk.Frame(self.top_shell, bg="#0a0f1d")
        mid.pack(side="left", fill="both", expand=True)

        right = tk.Frame(self.top_shell, bg="#0a0f1d")
        right.pack(side="right", fill="y", padx=8)

        self.app_title = tk.Label(
            left,
            text="JuggerNei8",
            bg="#0a0f1d",
            fg=self.text_fg,
            font=(self.font_family, 15, "bold"),
        )
        self.app_title.pack(side="left", padx=(8, 18), pady=10)

        nav_cfg = {"bg": "#0a0f1d", "fg": self.text_fg, "activebackground": "#161d31", "relief": "flat", "bd": 0}
        self.nav_live = tk.Button(mid, text="Match Day", command=lambda: self.show_page("live_match"), **nav_cfg)
        self.nav_post = tk.Button(mid, text="Report", command=lambda: self.show_page("post_match"), **nav_cfg)
        self.nav_club = tk.Button(mid, text="Club", command=lambda: self.show_page("team_overview"), **nav_cfg)
        self.nav_squad = tk.Button(mid, text="Squad", command=lambda: self.show_page("player_stats"), **nav_cfg)
        self.nav_settings = tk.Button(mid, text="Settings", command=lambda: self.show_page("settings_home"), **nav_cfg)

        for btn in [self.nav_live, self.nav_post, self.nav_club, self.nav_squad, self.nav_settings]:
            btn.pack(side="left", padx=6, pady=8)

        self.global_search = tk.Entry(
            right,
            bg="#161d31",
            fg="white",
            insertbackground="white",
            relief="flat",
            width=24,
        )
        self.global_search.pack(side="left", padx=6, pady=12)
        self.global_search.insert(0, "Search")

        self.clock_top = tk.Label(
            right,
            text="09:00",
            bg="#0a0f1d",
            fg=self.text_fg,
            font=(self.font_family, 11, "bold"),
        )
        self.clock_top.pack(side="left", padx=10)

    def build_header_strip(self):
        self.header_strip = tk.Frame(self.main, bg=self.card_bg, height=82)
        self.header_strip.pack(fill="x")
        self.header_strip.pack_propagate(False)

        left = tk.Frame(self.header_strip, bg=self.card_bg)
        left.pack(side="left", fill="y", padx=10)

        center = tk.Frame(self.header_strip, bg=self.card_bg)
        center.pack(side="left", fill="both", expand=True)

        right = tk.Frame(self.header_strip, bg=self.card_bg)
        right.pack(side="right", fill="y", padx=12)

        self.home_logo_label = tk.Label(left, bg=self.card_bg, fg=self.text_fg)
        self.home_logo_label.pack(side="left", padx=(0, 6), pady=10)

        self.home_name_label = tk.Label(
            left,
            text="HOME",
            bg=self.card_bg,
            fg=self.text_fg,
            font=(self.font_family, self.header_font_size, "bold"),
        )
        self.home_name_label.pack(side="left", padx=4)

        self.score_label = tk.Label(
            center,
            text="0 - 0",
            bg=self.card_bg,
            fg=self.text_fg,
            font=(self.font_family, self.score_font_size, "bold"),
        )
        self.score_label.pack(side="left", padx=16, pady=8)

        self.away_name_label = tk.Label(
            center,
            text="AWAY",
            bg=self.card_bg,
            fg=self.text_fg,
            font=(self.font_family, self.header_font_size, "bold"),
        )
        self.away_name_label.pack(side="left", padx=4)

        self.away_logo_label = tk.Label(center, bg=self.card_bg, fg=self.text_fg)
        self.away_logo_label.pack(side="left", padx=(6, 16), pady=10)

        self.prediction_label = tk.Label(
            center,
            text="Prediction: waiting",
            bg=self.card_bg,
            fg="#ffd166",
            font=(self.font_family, self.body_font_size + 1, "bold"),
            wraplength=520,
            justify="left",
        )
        self.prediction_label.pack(side="left", padx=10)

        self.backend_indicator = tk.Label(
            right,
            text="● Checking backend",
            bg=self.card_bg,
            fg="#facc15",
            font=(self.font_family, self.body_font_size, "bold"),
        )
        self.backend_indicator.pack(anchor="e", pady=(10, 4))

        self.clock_label = tk.Label(
            right,
            text="00:00",
            bg=self.card_bg,
            fg=self.text_fg,
            font=(self.font_family, self.header_font_size + 4, "bold"),
        )
        self.clock_label.pack(anchor="e")

        self.possession_label = tk.Label(
            right,
            text="Possession 50% - 50%",
            bg=self.card_bg,
            fg=self.text_fg,
            font=(self.font_family, self.body_font_size),
        )
        self.possession_label.pack(anchor="e", pady=(4, 0))

    def build_page_host(self):
        self.page_host = tk.Frame(self.main, bg=self.theme_bg)
        self.page_host.pack(fill="both", expand=True)

    def build_pages(self):
        self.pages = {}

        for name in [
            "live_match",
            "post_match",
            "team_overview",
            "player_stats",
            "settings_home",
            "personalization",
        ]:
            frame = tk.Frame(self.page_host, bg=self.theme_bg)
            self.pages[name] = frame

        self.build_live_match_page()
        self.build_post_match_page()
        self.build_team_overview_page()
        self.build_player_stats_page()
        self.build_settings_home_page()
        self.build_personalization_page()

    def show_page(self, page_name: str):
        for frame in self.pages.values():
            frame.pack_forget()

        self.current_page = page_name
        self.pages[page_name].pack(fill="both", expand=True)
        self.highlight_nav()

    def highlight_nav(self):
        nav_map = {
            "live_match": self.nav_live,
            "post_match": self.nav_post,
            "team_overview": self.nav_club,
            "player_stats": self.nav_squad,
            "settings_home": self.nav_settings,
            "personalization": self.nav_settings,
        }
        for btn in [self.nav_live, self.nav_post, self.nav_club, self.nav_squad, self.nav_settings]:
            btn.configure(bg="#0a0f1d")
        current = nav_map.get(self.current_page)
        if current:
            current.configure(bg="#1a2137")

    def make_card(self, parent, title: str):
        card = tk.LabelFrame(parent, text=title, bg=self.card_bg, fg=self.text_fg, bd=1, padx=10, pady=10)
        return card

    # ------------------------------------------------
    # LIVE MATCH PAGE
    # ------------------------------------------------

    def build_live_match_page(self):
        page = self.pages["live_match"]

        top = tk.Frame(page, bg=self.theme_bg)
        top.pack(fill="x", padx=10, pady=(10, 6))

        self.live_detail_label = tk.Label(
            top,
            text="Live Match Dashboard",
            bg=self.theme_bg,
            fg=self.text_fg,
            font=(self.font_family, 18, "bold"),
        )
        self.live_detail_label.pack(side="left")

        self.live_page_status = tk.Label(
            top,
            text="Broadcast view",
            bg=self.theme_bg,
            fg=self.accent,
            font=(self.font_family, self.body_font_size, "bold"),
        )
        self.live_page_status.pack(side="right")

        body = tk.Frame(page, bg=self.theme_bg)
        body.pack(fill="both", expand=True, padx=10, pady=(0, 10))

        self.live_left = tk.Frame(body, bg=self.theme_bg, width=310)
        self.live_left.pack(side="left", fill="y", padx=(0, 6))
        self.live_left.pack_propagate(False)

        self.live_center = tk.Frame(body, bg=self.theme_bg)
        self.live_center.pack(side="left", fill="both", expand=True, padx=6)

        self.live_right = tk.Frame(body, bg=self.theme_bg, width=360)
        self.live_right.pack(side="right", fill="y", padx=(6, 0))
        self.live_right.pack_propagate(False)

        self.build_live_left_column()
        self.build_live_center_column()
        self.build_live_right_column()

    def build_live_left_column(self):
        card = self.make_card(self.live_left, "Match Controls")
        card.pack(fill="x", pady=(0, 8))

        tk.Label(card, text="League", bg=self.card_bg, fg=self.text_fg).pack(anchor="w")
        self.league_box = ttk.Combobox(card, values=list(LEAGUE_OPTIONS.keys()), state="readonly")
        self.league_box.pack(fill="x", pady=(2, 8))
        self.league_box.set(self._league_name_from_code(self.current_competition))
        self.league_box.bind("<<ComboboxSelected>>", self.on_league_changed)

        home_row = tk.Frame(card, bg=self.card_bg)
        home_row.pack(fill="x", pady=3)
        tk.Label(home_row, text="Home", bg=self.card_bg, fg=self.text_fg, width=8, anchor="w").pack(side="left")
        self.home_box = ttk.Combobox(home_row, values=self.team_list, state="normal")
        self.home_box.pack(side="left", fill="x", expand=True)
        self.home_box.bind("<<ComboboxSelected>>", self.on_team_selection_changed)

        away_row = tk.Frame(card, bg=self.card_bg)
        away_row.pack(fill="x", pady=3)
        tk.Label(away_row, text="Away", bg=self.card_bg, fg=self.text_fg, width=8, anchor="w").pack(side="left")
        self.away_box = ttk.Combobox(away_row, values=self.team_list, state="normal")
        self.away_box.pack(side="left", fill="x", expand=True)
        self.away_box.bind("<<ComboboxSelected>>", self.on_team_selection_changed)

        tk.Label(card, text="Home Formation", bg=self.card_bg, fg=self.text_fg).pack(anchor="w", pady=(8, 0))
        self.home_formation_box = ttk.Combobox(card, values=["4-3-3", "4-2-3-1", "4-4-2", "3-5-2"], state="readonly")
        self.home_formation_box.pack(fill="x", pady=(2, 6))
        self.home_formation_box.set("4-3-3")

        tk.Label(card, text="Away Formation", bg=self.card_bg, fg=self.text_fg).pack(anchor="w")
        self.away_formation_box = ttk.Combobox(card, values=["4-3-3", "4-2-3-1", "4-4-2", "3-5-2"], state="readonly")
        self.away_formation_box.pack(fill="x", pady=(2, 8))
        self.away_formation_box.set("4-2-3-1")

        btn_cfg = {"bg": self.accent, "fg": "white", "relief": "flat", "activebackground": self.accent}
        tk.Button(card, text="Start Match", command=self.start_match, **btn_cfg).pack(fill="x", pady=3)
        tk.Button(card, text="Pause Match", command=self.pause_match, **btn_cfg).pack(fill="x", pady=3)
        tk.Button(card, text="Reset Match", command=self.reset_match, **btn_cfg).pack(fill="x", pady=3)
        tk.Button(card, text="Refresh Data", command=self.load_initial_data, **btn_cfg).pack(fill="x", pady=3)
        tk.Button(card, text="Settings", command=lambda: self.show_page("settings_home"), **btn_cfg).pack(fill="x", pady=3)

        info_card = self.make_card(self.live_left, "Live Notes")
        info_card.pack(fill="both", expand=True)

        self.tactic_label = tk.Label(
            info_card,
            text="Live tactics: waiting",
            bg=self.card_bg,
            fg="#cbd5e1",
            justify="left",
            wraplength=250,
            anchor="nw",
        )
        self.tactic_label.pack(fill="x", pady=4)

        self.form_label = tk.Label(
            info_card,
            text="Team form: waiting",
            bg=self.card_bg,
            fg="#93c5fd",
            justify="left",
            wraplength=250,
            anchor="nw",
        )
        self.form_label.pack(fill="x", pady=4)

        self.commentary_box = tk.Text(info_card, height=16, bg="#09111f", fg="white", relief="flat", wrap="word")
        self.commentary_box.pack(fill="both", expand=True, pady=(8, 0))

    def build_live_center_column(self):
        score_card = self.make_card(self.live_center, "Live Match")
        score_card.pack(fill="x", pady=(0, 8))

        self.live_match_detail = tk.Label(
            score_card,
            text="Home vs Away | 00:00",
            bg=self.card_bg,
            fg=self.text_fg,
            font=(self.font_family, 13, "bold"),
        )
        self.live_match_detail.pack(anchor="w")

        self.canvas = tk.Canvas(
            self.live_center,
            bg=self.pitch_bg,
            highlightthickness=0,
            cursor="crosshair",
            height=420,
        )
        self.canvas.pack(fill="both", expand=True, pady=(0, 8))

        bottom_row = tk.Frame(self.live_center, bg=self.theme_bg)
        bottom_row.pack(fill="x")

        stats_card = self.make_card(bottom_row, "Match Stats")
        stats_card.pack(side="left", fill="both", expand=True, padx=(0, 4))
        self.stats_box = tk.Text(stats_card, height=10, bg="#09111f", fg="white", relief="flat", wrap="word")
        self.stats_box.pack(fill="both", expand=True)

        timeline_card = self.make_card(bottom_row, "Match Events")
        timeline_card.pack(side="left", fill="both", expand=True, padx=(4, 0))
        self.timeline_box = tk.Text(timeline_card, height=10, bg="#09111f", fg="white", relief="flat", wrap="word")
        self.timeline_box.pack(fill="both", expand=True)

    def build_live_right_column(self):
        compare = self.make_card(self.live_right, "Comparison")
        compare.pack(fill="x", pady=(0, 8))

        self.compare_title = tk.Label(compare, text="Home vs Away", bg=self.card_bg, fg=self.text_fg, font=(self.font_family, 11, "bold"))
        self.compare_title.pack(anchor="w")

        self.compare_record_label = tk.Label(compare, text="Wins recent: -", bg=self.card_bg, fg=self.text_fg)
        self.compare_record_label.pack(anchor="w", pady=(6, 2))

        self.wins_bar = tk.Canvas(compare, height=18, bg="#09111f", highlightthickness=0)
        self.wins_bar.pack(fill="x", pady=(0, 6))

        self.compare_goals_label = tk.Label(compare, text="Goals recent: -", bg=self.card_bg, fg=self.text_fg)
        self.compare_goals_label.pack(anchor="w", pady=(2, 2))

        self.goals_bar = tk.Canvas(compare, height=18, bg="#09111f", highlightthickness=0)
        self.goals_bar.pack(fill="x")

        odds_card = self.make_card(self.live_right, "Selected Match Odds")
        odds_card.pack(fill="x", pady=(0, 8))

        odds_row = tk.Frame(odds_card, bg=self.card_bg)
        odds_row.pack(fill="x")
        self.odds_card_home_value = self._make_odds_box(odds_row, "HOME")
        self.odds_card_draw_value = self._make_odds_box(odds_row, "DRAW")
        self.odds_card_away_value = self._make_odds_box(odds_row, "AWAY")

        self.live_box = self._make_text_panel(self.live_right, "Live Games", 9)
        self.table_box = self._make_text_panel(self.live_right, "Live Table", 9)

    # ------------------------------------------------
    # POST MATCH PAGE
    # ------------------------------------------------

    def build_post_match_page(self):
        page = self.pages["post_match"]

        title = tk.Label(
            page,
            text="Post Match Report",
            bg=self.theme_bg,
            fg=self.text_fg,
            font=(self.font_family, 18, "bold"),
        )
        title.pack(anchor="w", padx=10, pady=(10, 6))

        top = tk.Frame(page, bg=self.theme_bg)
        top.pack(fill="x", padx=10, pady=(0, 8))

        self.post_score_banner = tk.Label(
            top,
            text="Home 0 - 0 Away",
            bg=self.card_bg,
            fg=self.text_fg,
            font=(self.font_family, 20, "bold"),
            pady=16,
        )
        self.post_score_banner.pack(fill="x")

        body = tk.Frame(page, bg=self.theme_bg)
        body.pack(fill="both", expand=True, padx=10, pady=(0, 10))

        left = tk.Frame(body, bg=self.theme_bg, width=300)
        left.pack(side="left", fill="y", padx=(0, 6))
        left.pack_propagate(False)

        center = tk.Frame(body, bg=self.theme_bg)
        center.pack(side="left", fill="both", expand=True, padx=6)

        right = tk.Frame(body, bg=self.theme_bg, width=320)
        right.pack(side="right", fill="y", padx=(6, 0))
        right.pack_propagate(False)

        self.report_home_box = self._make_text_panel(left, "Home Ratings", 18)
        self.report_away_box = self._make_text_panel(right, "Away Ratings", 18)

        self.post_events_box = self._make_text_panel(center, "Match Events", 10)
        self.post_stats_box = self._make_text_panel(center, "Match Statistics", 10)
        self.post_latest_box = self._make_text_panel(right, "Latest Scores", 8)
        self.post_table_box = self._make_text_panel(right, "League Table", 8)

    # ------------------------------------------------
    # TEAM OVERVIEW PAGE
    # ------------------------------------------------

    def build_team_overview_page(self):
        page = self.pages["team_overview"]

        header = tk.Label(
            page,
            text="Team Overview",
            bg=self.theme_bg,
            fg=self.text_fg,
            font=(self.font_family, 18, "bold"),
        )
        header.pack(anchor="w", padx=10, pady=(10, 6))

        top = tk.Frame(page, bg=self.theme_bg)
        top.pack(fill="x", padx=10, pady=(0, 8))

        self.team_overview_head = tk.Label(
            top,
            text="Club overview page",
            bg=self.card_bg,
            fg=self.text_fg,
            font=(self.font_family, 16, "bold"),
            pady=14,
        )
        self.team_overview_head.pack(fill="x")

        body = tk.Frame(page, bg=self.theme_bg)
        body.pack(fill="both", expand=True, padx=10, pady=(0, 10))

        left = tk.Frame(body, bg=self.theme_bg, width=310)
        left.pack(side="left", fill="y", padx=(0, 6))
        left.pack_propagate(False)

        center = tk.Frame(body, bg=self.theme_bg)
        center.pack(side="left", fill="both", expand=True, padx=6)

        right = tk.Frame(body, bg=self.theme_bg, width=320)
        right.pack(side="right", fill="y", padx=(6, 0))
        right.pack_propagate(False)

        self.club_staff_box = self._make_text_panel(left, "Staff / Team Snapshot", 14)
        self.club_history_box = self._make_text_panel(left, "Club History", 10)

        self.club_fixtures_box = self._make_text_panel(center, "Fixtures and Results", 14)
        self.club_graph_box = self._make_text_panel(center, "Club History Graph Data", 10)

        self.club_player_stats_box = self._make_text_panel(right, "Player Stats", 10)
        self.club_tactical_box = self._make_text_panel(right, "Tactical Profile", 8)
        self.club_transfer_box = self._make_text_panel(right, "Transfer History", 8)

    # ------------------------------------------------
    # PLAYER STATS PAGE
    # ------------------------------------------------

    def build_player_stats_page(self):
        page = self.pages["player_stats"]

        header = tk.Label(
            page,
            text="Player / Staff Stats",
            bg=self.theme_bg,
            fg=self.text_fg,
            font=(self.font_family, 18, "bold"),
        )
        header.pack(anchor="w", padx=10, pady=(10, 6))

        self.player_head = tk.Label(
            page,
            text="Player profile and attributes",
            bg=self.card_bg,
            fg=self.text_fg,
            font=(self.font_family, 16, "bold"),
            pady=14,
        )
        self.player_head.pack(fill="x", padx=10, pady=(0, 8))

        body = tk.Frame(page, bg=self.theme_bg)
        body.pack(fill="both", expand=True, padx=10, pady=(0, 10))

        left = tk.Frame(body, bg=self.theme_bg, width=250)
        left.pack(side="left", fill="y", padx=(0, 6))
        left.pack_propagate(False)

        center = tk.Frame(body, bg=self.theme_bg)
        center.pack(side="left", fill="both", expand=True, padx=6)

        right = tk.Frame(body, bg=self.theme_bg, width=300)
        right.pack(side="right", fill="y", padx=(6, 0))
        right.pack_propagate(False)

        self.player_role_box = self._make_text_panel(left, "Position / Role", 10)
        self.player_left_meta_box = self._make_text_panel(left, "Player Form / Happiness", 10)

        self.player_attributes_box = self._make_text_panel(center, "Attributes Overview", 22)

        self.player_info_box = self._make_text_panel(right, "Info", 8)
        self.player_season_box = self._make_text_panel(right, "Season Stats", 8)
        self.player_career_box = self._make_text_panel(right, "Career Stats", 8)

    # ------------------------------------------------
    # SETTINGS PAGES
    # ------------------------------------------------

    def build_settings_home_page(self):
        page = self.pages["settings_home"]

        title = tk.Label(
            page,
            text="Settings",
            bg=self.theme_bg,
            fg=self.text_fg,
            font=(self.font_family, 18, "bold"),
        )
        title.pack(anchor="w", padx=10, pady=(10, 6))

        card = self.make_card(page, "Match View / System")
        card.pack(fill="x", padx=10, pady=(0, 8))

        tk.Label(
            card,
            text="Choose camera style, graphics quality, match sounds, and personalization.",
            bg=self.card_bg,
            fg=self.text_fg,
            justify="left",
        ).pack(anchor="w", pady=(0, 10))

        tk.Button(card, text="Personalization", command=lambda: self.show_page("personalization"), bg=self.accent, fg="white", relief="flat").pack(fill="x", pady=4)
        tk.Button(card, text="High Refresh", command=lambda: self.set_refresh_quality("high"), bg=self.accent, fg="white", relief="flat").pack(fill="x", pady=4)
        tk.Button(card, text="Balanced Refresh", command=lambda: self.set_refresh_quality("balanced"), bg=self.accent, fg="white", relief="flat").pack(fill="x", pady=4)
        tk.Button(card, text="Saver Refresh", command=lambda: self.set_refresh_quality("saver"), bg=self.accent, fg="white", relief="flat").pack(fill="x", pady=4)
        tk.Button(card, text="Mute / Unmute", command=self.toggle_mute, bg=self.accent, fg="white", relief="flat").pack(fill="x", pady=4)

        note = self.make_card(page, "Design Note")
        note.pack(fill="x", padx=10, pady=(0, 10))
        tk.Label(
            note,
            text="This settings page is the parent page. Personalization is nested under Settings.",
            bg=self.card_bg,
            fg=self.accent2,
            justify="left",
        ).pack(anchor="w")

    def build_personalization_page(self):
        page = self.pages["personalization"]

        title = tk.Label(
            page,
            text="Settings > Personalization",
            bg=self.theme_bg,
            fg=self.text_fg,
            font=(self.font_family, 18, "bold"),
        )
        title.pack(anchor="w", padx=10, pady=(10, 6))

        body = tk.Frame(page, bg=self.theme_bg)
        body.pack(fill="both", expand=True, padx=10, pady=(0, 10))

        left = tk.Frame(body, bg=self.theme_bg, width=360)
        left.pack(side="left", fill="y", padx=(0, 6))
        left.pack_propagate(False)

        center = tk.Frame(body, bg=self.theme_bg)
        center.pack(side="left", fill="both", expand=True, padx=6)

        right = tk.Frame(body, bg=self.theme_bg, width=260)
        right.pack(side="right", fill="y", padx=(6, 0))
        right.pack_propagate(False)

        fonts_card = self.make_card(left, "Fonts")
        fonts_card.pack(fill="x", pady=(0, 8))

        tk.Label(fonts_card, text="Font family", bg=self.card_bg, fg=self.text_fg).grid(row=0, column=0, sticky="w", pady=4)
        self.font_family_box = ttk.Combobox(fonts_card, values=FONT_FAMILIES, state="readonly")
        self.font_family_box.grid(row=0, column=1, sticky="ew", pady=4, padx=6)
        self.font_family_box.set(self.font_family)

        tk.Label(fonts_card, text="Header size", bg=self.card_bg, fg=self.text_fg).grid(row=1, column=0, sticky="w", pady=4)
        self.header_size_spin = tk.Spinbox(fonts_card, from_=12, to=28, width=10)
        self.header_size_spin.grid(row=1, column=1, sticky="w", pady=4, padx=6)
        self.header_size_spin.delete(0, "end")
        self.header_size_spin.insert(0, str(self.header_font_size))

        tk.Label(fonts_card, text="Body size", bg=self.card_bg, fg=self.text_fg).grid(row=2, column=0, sticky="w", pady=4)
        self.body_size_spin = tk.Spinbox(fonts_card, from_=8, to=20, width=10)
        self.body_size_spin.grid(row=2, column=1, sticky="w", pady=4, padx=6)
        self.body_size_spin.delete(0, "end")
        self.body_size_spin.insert(0, str(self.body_font_size))

        tk.Label(fonts_card, text="Score size", bg=self.card_bg, fg=self.text_fg).grid(row=3, column=0, sticky="w", pady=4)
        self.score_size_spin = tk.Spinbox(fonts_card, from_=20, to=48, width=10)
        self.score_size_spin.grid(row=3, column=1, sticky="w", pady=4, padx=6)
        self.score_size_spin.delete(0, "end")
        self.score_size_spin.insert(0, str(self.score_font_size))

        fonts_card.columnconfigure(1, weight=1)

        theme_card = self.make_card(center, "Themes and Colors")
        theme_card.pack(fill="x", pady=(0, 8))

        tk.Label(theme_card, text="Preset theme", bg=self.card_bg, fg=self.text_fg).grid(row=0, column=0, sticky="w", pady=4)
        self.theme_box = ttk.Combobox(theme_card, values=list(THEME_PRESETS.keys()), state="readonly")
        self.theme_box.grid(row=0, column=1, sticky="ew", pady=4, padx=6)
        self.theme_box.set("Broadcast Purple")

        tk.Label(theme_card, text="Pitch color", bg=self.card_bg, fg=self.text_fg).grid(row=1, column=0, sticky="w", pady=4)
        self.pitch_color_box = ttk.Combobox(theme_card, values=["#2e7d32", "#1f8f46", "#3f9c35", "#245b2a", "#4caf50"], state="readonly")
        self.pitch_color_box.grid(row=1, column=1, sticky="ew", pady=4, padx=6)
        self.pitch_color_box.set(self.pitch_bg)

        theme_card.columnconfigure(1, weight=1)

        bg_card = self.make_card(center, "Backgrounds")
        bg_card.pack(fill="x", pady=(0, 8))

        self.main_bg_label = tk.Label(bg_card, text="Main image: not set", bg=self.card_bg, fg=self.text_fg, anchor="w")
        self.main_bg_label.pack(fill="x", pady=3)
        tk.Button(bg_card, text="Choose Main Background", command=lambda: self.choose_background("main"), bg=self.accent, fg="white", relief="flat").pack(fill="x", pady=2)

        self.general_bg_label = tk.Label(bg_card, text="General image: not set", bg=self.card_bg, fg=self.text_fg, anchor="w")
        self.general_bg_label.pack(fill="x", pady=3)
        tk.Button(bg_card, text="Choose General Background", command=lambda: self.choose_background("general"), bg=self.accent, fg="white", relief="flat").pack(fill="x", pady=2)

        self.pitch_bg_label = tk.Label(bg_card, text="Pitch image: not set", bg=self.card_bg, fg=self.text_fg, anchor="w")
        self.pitch_bg_label.pack(fill="x", pady=3)
        tk.Button(bg_card, text="Choose Pitch Background", command=lambda: self.choose_background("pitch"), bg=self.accent, fg="white", relief="flat").pack(fill="x", pady=2)

        self.stadium_bg_label = tk.Label(bg_card, text="Stadium image: not set", bg=self.card_bg, fg=self.text_fg, anchor="w")
        self.stadium_bg_label.pack(fill="x", pady=3)
        tk.Button(bg_card, text="Choose Stadium Background", command=lambda: self.choose_background("stadium"), bg=self.accent, fg="white", relief="flat").pack(fill="x", pady=2)

        side_card = self.make_card(right, "Actions")
        side_card.pack(fill="x")

        tk.Button(side_card, text="OK", command=self.apply_personalization_settings, bg=self.accent, fg="white", relief="flat").pack(fill="x", pady=4)
        tk.Button(side_card, text="Back", command=lambda: self.show_page("settings_home"), bg=self.accent2, fg="white", relief="flat").pack(fill="x", pady=4)

        tk.Label(
            side_card,
            text="Recommended background folder:\nC:\\Project X\\codex-environment-main\\src\\assets\\backgrounds\\",
            bg=self.card_bg,
            fg=self.accent2,
            justify="left",
        ).pack(anchor="w", pady=(10, 0))

    # ------------------------------------------------
    # WIDGET BUILD HELPERS
    # ------------------------------------------------

    def _make_odds_box(self, parent, title):
        box = tk.Frame(parent, bg="#09111f", padx=10, pady=8)
        box.pack(side="left", expand=True, fill="both", padx=4)
        tk.Label(box, text=title, bg="#09111f", fg=self.accent2, font=(self.font_family, self.body_font_size - 1, "bold")).pack()
        value_label = tk.Label(box, text="-", bg="#09111f", fg="white", font=(self.font_family, self.body_font_size + 4, "bold"))
        value_label.pack()
        return value_label

    def _make_text_panel(self, parent, title, height):
        wrap = self.make_card(parent, title)
        wrap.pack(fill="x", pady=4)
        box = tk.Text(wrap, height=height, bg="#09111f", fg="white", relief="flat", wrap="word")
        box.pack(fill="x")
        return box

    # ------------------------------------------------
    # SAFE CALLBACKS
    # ------------------------------------------------

    def add_commentary(self, text):
        if hasattr(self, "commentary_box"):
            self.commentary_box.insert("end", text + "\n")
            self.commentary_box.see("end")

    def update_stats(self, stats):
        if not hasattr(self, "stats_box"):
            return
        self.stats_box.delete("1.0", "end")
        self.stats_box.insert("end", f"Home Shots: {stats.get('home_shots', 0)}\n")
        self.stats_box.insert("end", f"Away Shots: {stats.get('away_shots', 0)}\n")
        self.stats_box.insert("end", f"Home On Target: {stats.get('home_on_target', 0)}\n")
        self.stats_box.insert("end", f"Away On Target: {stats.get('away_on_target', 0)}\n")
        self.stats_box.insert("end", f"Home Passes: {stats.get('home_passes', 0)}\n")
        self.stats_box.insert("end", f"Away Passes: {stats.get('away_passes', 0)}\n")
        self.stats_box.insert("end", f"Home Saves: {stats.get('home_saves', 0)}\n")
        self.stats_box.insert("end", f"Away Saves: {stats.get('away_saves', 0)}\n")

        if hasattr(self, "post_stats_box"):
            self.post_stats_box.delete("1.0", "end")
            for k, v in stats.items():
                self.post_stats_box.insert("end", f"{k}: {v}\n")

    def add_timeline_event(self, minute, kind, text):
        self.timeline_engine.add_event(minute, kind, text)
        if hasattr(self, "timeline_box"):
            self.timeline_box.delete("1.0", "end")
            for line in self.timeline_engine.as_lines(limit=24):
                self.timeline_box.insert("end", line + "\n")
        if hasattr(self, "post_events_box"):
            self.post_events_box.delete("1.0", "end")
            for line in self.timeline_engine.as_lines(limit=24):
                self.post_events_box.insert("end", line + "\n")

    # ------------------------------------------------
    # BACKEND / DATA
    # ------------------------------------------------

    def set_backend_indicator(self, online: bool, source: str = "unknown"):
        self.backend_online = online
        self.last_data_source = source
        if online:
            self.backend_indicator.config(text="● Backend Online", fg="#22c55e")
        else:
            self.backend_indicator.config(text="● Offline / Cache Mode", fg="#f59e0b")

    def startup_backend_then_load(self):
        self.add_commentary("Checking backend status...")
        if hasattr(self, "backend_indicator"):
            self.backend_indicator.config(text="● Checking backend", fg="#facc15")
        run_in_background(self._ensure_backend_running, self._on_backend_ready, self._on_backend_error)

    def _ensure_backend_running(self):
        if self.backend_launcher.is_backend_running():
            return {"started": False, "ready": True}
        started = self.backend_launcher.start_backend()
        return {"started": True, "ready": started}

    def _on_backend_ready(self, result):
        if result and result.get("ready"):
            self.set_backend_indicator(True, "backend")
            self.add_commentary("Backend ready.")
        else:
            self.set_backend_indicator(False, "cache")
            self.add_commentary("Backend unavailable. Falling back to cache/local mode.")
        self.load_initial_data()

    def _on_backend_error(self, error):
        logger.exception("Backend startup error: %s", error)
        self.set_backend_indicator(False, "cache")
        self.add_commentary("Backend startup failed. Using cache/local mode.")
        self.load_initial_data()

    def load_initial_data(self):
        run_in_background(self._fetch_all_data, self._on_data_loaded, self._on_data_error)

    def _fetch_all_data(self):
        comp = self.current_competition
        return {
            "teams": self.data_client.load_teams(comp),
            "fixtures": self.data_client.load_fixtures(comp),
            "standings": self.data_client.load_standings(comp),
            "news": self.data_client.load_news(comp),
            "usage": self.data_client.load_usage(),
            "export_status": self.data_client.load_export_status(),
            "live_games": self.data_client.load_live_games(),
            "odds_markets": self.data_client.load_odds_markets(),
            "bet365_prematch": self.data_client.load_bet365_prematch(),
            "tournament_odds": self.data_client.load_odds_tournaments("17"),
        }

    def _on_data_loaded(self, data):
        if not data:
            self.set_backend_indicator(False, "cache")
            return

        self.teams = data.get("teams", []) or []
        self.fixtures = data.get("fixtures", []) or []
        self.standings = data.get("standings", []) or []
        self.news_items = data.get("news", []) or []
        self.backend_usage = data.get("usage", {}) or {}
        self.export_status = data.get("export_status", {}) or {}
        self.live_games = data.get("live_games", {}) or {}
        self.odds_markets = data.get("odds_markets", {}) or {}
        self.bet365_prematch = data.get("bet365_prematch", {}) or {}
        self.tournament_odds = data.get("tournament_odds", {}) or {}

        self.team_list = sorted({t.get("name", "").strip() for t in self.teams if isinstance(t, dict) and t.get("name")})

        self.reload_selectors()
        self.refresh_all_display()
        self.populate_demo_pages()
        self.add_commentary(f"Loaded {len(self.team_list)} teams.")

    def _on_data_error(self, error):
        logger.exception("Data load error: %s", error)
        self.set_backend_indicator(False, "cache")
        self.add_commentary("Failed to refresh backend data.")

    def schedule_live_refresh_loop(self):
        self.root.after(self.live_refresh_ms, self._live_refresh_wrapper)

    def _live_refresh_wrapper(self):
        run_in_background(self._fetch_all_data, self._on_data_loaded, self._on_data_error)
        self.schedule_live_refresh_loop()

    def reload_selectors(self):
        self.home_box["values"] = self.team_list
        self.away_box["values"] = self.team_list
        if len(self.team_list) >= 2:
            if not self.home_box.get() or self.home_box.get() not in self.team_list:
                self.home_box.set(self.team_list[0])
            if not self.away_box.get() or self.away_box.get() not in self.team_list:
                self.away_box.set(self.team_list[1])

    # ------------------------------------------------
    # PAGE DATA RENDER
    # ------------------------------------------------

    def refresh_all_display(self):
        self.refresh_match_detail()
        self.refresh_compare_card()
        self.reload_live_panels()

    def refresh_match_detail(self):
        home = self.home_box.get().strip() or "Home"
        away = self.away_box.get().strip() or "Away"

        self.live_match_detail.config(text=f"{home} vs {away} | {self.clock_label.cget('text')}")
        self.home_name_label.config(text=home)
        self.away_name_label.config(text=away)

        self.load_header_logos(home, away)

    def refresh_compare_card(self):
        home = self.home_box.get().strip() or "Home"
        away = self.away_box.get().strip() or "Away"
        hf = self.home_form_data or {}
        af = self.away_form_data or {}

        hw = int(hf.get("wins_recent", 0))
        aw = int(af.get("wins_recent", 0))
        hgf = int(hf.get("goals_for_recent", 0))
        agf = int(af.get("goals_for_recent", 0))
        hga = int(hf.get("goals_against_recent", 0))
        aga = int(af.get("goals_against_recent", 0))

        self.compare_title.config(text=f"{home} vs {away}")
        self.compare_record_label.config(text=f"Wins recent: {home} {hw} | {away} {aw}")
        self.compare_goals_label.config(text=f"Goals recent: {home} {hgf}-{hga} | {away} {agf}-{aga}")

        self._render_form_bar(self.wins_bar, self._safe_ratio(hw, aw), 100 - self._safe_ratio(hw, aw))
        self._render_form_bar(self.goals_bar, self._safe_ratio(hgf, agf), 100 - self._safe_ratio(hgf, agf))

    def reload_live_panels(self):
        self.live_box.delete("1.0", "end")
        self.table_box.delete("1.0", "end")

        live_matches = self.live_games.get("live_matches", []) if isinstance(self.live_games, dict) else []
        scheduled = self.live_games.get("scheduled_with_odds", []) if isinstance(self.live_games, dict) else []

        if live_matches:
            for m in live_matches[:12]:
                self.live_box.insert("end", f"{m.get('home','')} {m.get('score_home','?')}-{m.get('score_away','?')} {m.get('away','')}  {m.get('minute','')} {m.get('status','LIVE')}\n")
        elif scheduled:
            for m in scheduled[:12]:
                self.live_box.insert("end", f"{m.get('home','')} vs {m.get('away','')}  {m.get('status','')}  {m.get('start_time','')}\n")
        else:
            self.live_box.insert("end", "No live games loaded yet.\n")

        if self.standings:
            for row in self.standings[:20]:
                self.table_box.insert("end", f"{row.get('team','')}  P:{row.get('played',0)}  Pts:{row.get('points',0)}\n")
        else:
            self.table_box.insert("end", "No standings loaded.\n")

        self._render_selected_odds()

    def populate_demo_pages(self):
        self.club_staff_box.delete("1.0", "end")
        self.club_history_box.delete("1.0", "end")
        self.club_fixtures_box.delete("1.0", "end")
        self.club_graph_box.delete("1.0", "end")
        self.club_player_stats_box.delete("1.0", "end")
        self.club_tactical_box.delete("1.0", "end")
        self.club_transfer_box.delete("1.0", "end")

        self.player_role_box.delete("1.0", "end")
        self.player_left_meta_box.delete("1.0", "end")
        self.player_attributes_box.delete("1.0", "end")
        self.player_info_box.delete("1.0", "end")
        self.player_season_box.delete("1.0", "end")
        self.player_career_box.delete("1.0", "end")

        team = self.home_box.get().strip() or "Club"
        self.team_overview_head.config(text=f"{team} Overview")
        self.player_head.config(text=f"{team} Player / Staff Stats")

        self.club_staff_box.insert("end", f"Manager: Head Coach\nClub: {team}\nReputation: High\nTraining: Strong\nYouth: Good\n")
        self.club_history_box.insert("end", "Top league finish\nCup history\nEuropean history\nRecent form trends\n")
        for row in self.fixtures[:10]:
            self.club_fixtures_box.insert("end", f"{row.get('home','')} vs {row.get('away','')}  {row.get('status','')}\n")
        self.club_graph_box.insert("end", "Season ranking trend\nRevenue trend\nTransfer spend trend\n")
        self.club_player_stats_box.insert("end", "Top scorer\nMost assists\nHighest rating\nBest passer\n")
        self.club_tactical_box.insert("end", "Formation: 4-3-3\nPressing: Often\nStyle: Positive\n")
        self.club_transfer_box.insert("end", "Transfers in\nTransfers out\nNet spend\n")

        self.player_role_box.insert("end", "Role map\nPreferred positions\nTraits\n")
        self.player_left_meta_box.insert("end", "Happiness: Good\nForm: Strong\nDiscipline: OK\n")
        attrs = [
            "Crossing", "Dribbling", "Finishing", "First Touch", "Passing",
            "Tackling", "Marking", "Composure", "Aggression", "Vision",
            "Acceleration", "Balance", "Strength", "Stamina", "Pace"
        ]
        for a in attrs:
            self.player_attributes_box.insert("end", f"{a}: {random.randint(6, 20)}\n")
        self.player_info_box.insert("end", "Height: 185 cm\nReputation: Local\nPersonality: Determined\n")
        self.player_season_box.insert("end", "Apps: 0\nGoals: 0\nAssists: 0\nRating: 0.0\n")
        self.player_career_box.insert("end", "Career apps\nCareer goals\nClub history\n")

        self.post_latest_box.delete("1.0", "end")
        self.post_table_box.delete("1.0", "end")
        if self.fixtures:
            for row in self.fixtures[:8]:
                self.post_latest_box.insert("end", f"{row.get('home','')} vs {row.get('away','')}\n")
        if self.standings:
            for row in self.standings[:10]:
                self.post_table_box.insert("end", f"{row.get('team','')}  {row.get('points',0)} pts\n")

    # ------------------------------------------------
    # MATCH CONTROL
    # ------------------------------------------------

    def start_match(self):
        home = self.home_box.get().strip()
        away = self.away_box.get().strip()
        home_form = self.home_formation_box.get().strip()
        away_form = self.away_formation_box.get().strip()

        if not self.team_list:
            self.add_commentary("Cannot start match: no teams loaded")
            return
        if not home or not away:
            self.add_commentary("Please select both teams.")
            return

        self.home_score = 0
        self.away_score = 0
        self.match_time = 0
        self.match_finished = False

        self.score_label.config(text="0 - 0")
        self.post_score_banner.config(text=f"{home} 0 - 0 {away}")

        self.engine.configure_match(home, away, home_form, away_form)
        self.engine.frame_ms = 8 if self.fast_graphics else 12

        run_in_background(
            lambda: {
                "home_form": self.data_client.load_team_form(home, self.current_competition),
                "away_form": self.data_client.load_team_form(away, self.current_competition),
                "selected_fixture_odds": self.data_client.load_selected_fixture_odds(home, away),
            },
            lambda result: self._apply_pre_match_data(home, away, result),
            self._on_data_error,
        )

        if not self.engine.running:
            self.engine.running = True
            self.engine.animate()
            self.audio.play_crowd()
            self.add_commentary(f"{home} vs {away} kickoff!")
            self.show_page("live_match")

    def _apply_pre_match_data(self, home, away, result):
        self.home_form_data = result.get("home_form", {}) if result else {}
        self.away_form_data = result.get("away_form", {}) if result else {}
        self.selected_fixture_odds = result.get("selected_fixture_odds", {}) if result else {}

        prediction_text = self.prediction_engine.build_prediction(
            home=home,
            away=away,
            home_form=self.home_form_data,
            away_form=self.away_form_data,
            live_games=self.live_games,
            prematch_summary=self.bet365_prematch,
            tournament_odds=self.tournament_odds,
            fixture_odds=self.selected_fixture_odds,
        )

        self.prediction_label.config(text=prediction_text)
        self.form_label.config(
            text=(
                f"Team form\n"
                f"{home}: {' '.join(self.home_form_data.get('form_last5', [])) or 'n/a'}\n"
                f"{away}: {' '.join(self.away_form_data.get('form_last5', [])) or 'n/a'}"
            )
        )
        self.add_commentary(prediction_text)
        self.refresh_all_display()

    def pause_match(self):
        self.engine.running = False
        self.add_commentary("Match paused.")

    def reset_match(self):
        self.engine.reset_match()
        self.engine.running = False
        self.timeline_engine.clear()

        self.home_score = 0
        self.away_score = 0
        self.match_time = 0
        self.match_finished = False
        self.selected_fixture_odds = {}
        self.home_form_data = {}
        self.away_form_data = {}

        self.score_label.config(text="0 - 0")
        self.clock_label.config(text="00:00")
        self.possession_label.config(text="Possession 50% - 50%")
        self.prediction_label.config(text="Prediction: waiting")
        self.post_score_banner.config(text="Home 0 - 0 Away")

        if hasattr(self, "stats_box"):
            self.stats_box.delete("1.0", "end")
        if hasattr(self, "timeline_box"):
            self.timeline_box.delete("1.0", "end")
        if hasattr(self, "post_events_box"):
            self.post_events_box.delete("1.0", "end")
        if hasattr(self, "post_stats_box"):
            self.post_stats_box.delete("1.0", "end")

        self.form_label.config(text="Team form: waiting")
        self.refresh_all_display()
        self.add_commentary("Match reset.")

    def finish_match(self):
        if self.match_finished:
            return

        self.match_finished = True
        self.engine.running = False

        home = self.home_box.get().strip() or "Home"
        away = self.away_box.get().strip() or "Away"
        final_line = f"Full time: {home} {self.home_score} - {self.away_score} {away}"
        self.post_score_banner.config(text=f"{home} {self.home_score} - {self.away_score} {away}")
        self.add_commentary(final_line)

    # ------------------------------------------------
    # LIVE LOOPS / CALLBACKS
    # ------------------------------------------------

    def update_manager_tactics_loop(self):
        if hasattr(self, "engine") and self.engine.running and not self.match_finished:
            home_pos, away_pos = self.engine.get_possession_snapshot()

            home_shape = "attack" if self.home_score < self.away_score else "balanced"
            away_shape = "attack" if self.away_score < self.home_score else "balanced"

            self.engine.set_tactics(
                {"formation": self.home_formation_box.get(), "press": 0.58, "pass_speed": 1.0, "shot_bias": 0.11, "shape": home_shape},
                {"formation": self.away_formation_box.get(), "press": 0.58, "pass_speed": 1.0, "shot_bias": 0.11, "shape": away_shape},
            )

            self.tactic_label.config(
                text=(
                    f"Live tactics\n"
                    f"Home: {self.home_formation_box.get()} | {home_shape}\n"
                    f"Away: {self.away_formation_box.get()} | {away_shape}\n"
                    f"Possession: {home_pos}% - {away_pos}%"
                )
            )

        self.root.after(2000, self.update_manager_tactics_loop)

    def update_clock(self):
        if hasattr(self, "engine") and self.engine.running and not self.match_finished:
            self.match_time += 1
            minutes = self.match_time // 60
            seconds = self.match_time % 60
            clock_text = f"{minutes:02}:{seconds:02}"
            self.clock_label.config(text=clock_text)
            self.live_match_detail.config(text=f"{self.home_box.get().strip() or 'Home'} vs {self.away_box.get().strip() or 'Away'} | {clock_text}")

            if self.match_time >= self.match_duration_seconds:
                self.finish_match()

        self.root.after(1000, self.update_clock)

    def goal_scored(self, team):
        if team == "home":
            self.home_score += 1
        else:
            self.away_score += 1

        self.audio.play_goal()
        self.score_label.config(text=f"{self.home_score} - {self.away_score}")
        self.post_score_banner.config(text=f"{self.home_box.get().strip() or 'Home'} {self.home_score} - {self.away_score} {self.away_box.get().strip() or 'Away'}")
        self.add_commentary(self.commentary_engine.goal_commentary())

    def update_possession(self, home, away):
        self.possession_label.config(text=f"Possession {home}% - {away}%")

    # ------------------------------------------------
    # SETTINGS / PERSONALIZATION
    # ------------------------------------------------

    def apply_personalization_settings(self):
        try:
            self.font_family = self.font_family_box.get()
            self.header_font_size = int(self.header_size_spin.get())
            self.body_font_size = int(self.body_size_spin.get())
            self.score_font_size = int(self.score_size_spin.get())

            theme_name = self.theme_box.get()
            theme = THEME_PRESETS.get(theme_name, THEME_PRESETS["Broadcast Purple"])
            self.theme_bg = theme["theme_bg"]
            self.card_bg = theme["card_bg"]
            self.panel_bg = theme["panel_bg"]
            self.text_fg = theme["text_fg"]
            self.muted_fg = theme["muted_fg"]
            self.accent = theme["accent"]
            self.accent2 = theme["accent2"]
            self.pitch_bg = self.pitch_color_box.get() or theme["pitch_bg"]

            self.apply_theme_to_widgets()
            self.add_commentary("Personalization applied.")
            self.show_page("settings_home")
        except Exception as e:
            messagebox.showerror("Personalization", f"Could not apply settings:\n{e}")

    def choose_background(self, kind: str):
        path = filedialog.askopenfilename(
            title=f"Choose {kind} background",
            filetypes=[("Image files", "*.png *.jpg *.jpeg *.gif"), ("All files", "*.*")],
        )
        if not path:
            return

        if kind == "main":
            self.main_background_path = path
            self.main_bg_label.config(text=f"Main image: {path}")
        elif kind == "general":
            self.general_background_path = path
            self.general_bg_label.config(text=f"General image: {path}")
        elif kind == "pitch":
            self.pitch_background_path = path
            self.pitch_bg_label.config(text=f"Pitch image: {path}")
        elif kind == "stadium":
            self.stadium_background_path = path
            self.stadium_bg_label.config(text=f"Stadium image: {path}")

        self.add_commentary(f"{kind.title()} background set.")

    def apply_theme_to_widgets(self):
        self.root.configure(bg=self.theme_bg)
        self.main.configure(bg=self.theme_bg)
        self.page_host.configure(bg=self.theme_bg)

        self.app_title.configure(fg=self.text_fg)
        self.clock_top.configure(fg=self.text_fg)

        self.header_strip.configure(bg=self.card_bg)
        self.home_logo_label.configure(bg=self.card_bg, fg=self.text_fg)
        self.home_name_label.configure(bg=self.card_bg, fg=self.text_fg, font=(self.font_family, self.header_font_size, "bold"))
        self.score_label.configure(bg=self.card_bg, fg=self.text_fg, font=(self.font_family, self.score_font_size, "bold"))
        self.away_name_label.configure(bg=self.card_bg, fg=self.text_fg, font=(self.font_family, self.header_font_size, "bold"))
        self.away_logo_label.configure(bg=self.card_bg, fg=self.text_fg)
        self.prediction_label.configure(bg=self.card_bg, font=(self.font_family, self.body_font_size + 1, "bold"))
        self.backend_indicator.configure(bg=self.card_bg)
        self.clock_label.configure(bg=self.card_bg, fg=self.text_fg, font=(self.font_family, self.header_font_size + 4, "bold"))
        self.possession_label.configure(bg=self.card_bg, fg=self.text_fg, font=(self.font_family, self.body_font_size))

        self.canvas.configure(bg=self.pitch_bg)

    def set_refresh_quality(self, mode: str):
        if mode == "high":
            self.engine.frame_ms = 8
            self.fast_graphics = False
        elif mode == "balanced":
            self.engine.frame_ms = 12
            self.fast_graphics = False
        else:
            self.engine.frame_ms = 18
            self.fast_graphics = True
        self.add_commentary(f"Refresh quality set to {mode}.")

    def toggle_mute(self):
        self.audio_enabled = not self.audio_enabled
        self.audio.set_muted(not self.audio_enabled)
        self.add_commentary("Audio toggled.")

    # ------------------------------------------------
    # SELECTION HELPERS
    # ------------------------------------------------

    def on_league_changed(self, _event=None):
        selected = self.league_box.get()
        code = LEAGUE_OPTIONS.get(selected, "PL")
        self.current_competition = code
        self.add_commentary(f"League changed to {selected} ({code}). Refreshing data...")
        self.load_initial_data()

    def on_team_selection_changed(self, _event=None):
        home = self.home_box.get().strip()
        away = self.away_box.get().strip()

        self.refresh_match_detail()

        if home and away and home != away:
            run_in_background(
                lambda: {
                    "selected_fixture_odds": self.data_client.load_selected_fixture_odds(home, away),
                    "home_form": self.data_client.load_team_form(home, self.current_competition),
                    "away_form": self.data_client.load_team_form(away, self.current_competition),
                },
                self._on_selected_context_loaded,
                self._on_data_error,
            )

    def _on_selected_context_loaded(self, data):
        data = data or {}
        self.selected_fixture_odds = data.get("selected_fixture_odds", {}) or {}
        self.home_form_data = data.get("home_form", {}) or {}
        self.away_form_data = data.get("away_form", {}) or {}
        self.refresh_all_display()

    def _league_name_from_code(self, code):
        for name, value in LEAGUE_OPTIONS.items():
            if value == code:
                return name
        return "Premier League"

    def load_header_logos(self, home, away):
        home_logo = self.logo_loader.load(home, small=True)
        away_logo = self.logo_loader.load(away, small=True)

        if home_logo is not None:
            self.home_logo_label.config(image=home_logo, text="")
            self.home_logo_label.image = home_logo
        else:
            self.home_logo_label.config(image="", text=self.logo_loader.short_text_fallback(home), fg=self.text_fg)

        if away_logo is not None:
            self.away_logo_label.config(image=away_logo, text="")
            self.away_logo_label.image = away_logo
        else:
            self.away_logo_label.config(image="", text=self.logo_loader.short_text_fallback(away), fg=self.text_fg)

    def _render_selected_odds(self):
        self.odds_card_home_value.config(text="-")
        self.odds_card_draw_value.config(text="-")
        self.odds_card_away_value.config(text="-")

        selected = self.selected_fixture_odds.get("selected", {}) if isinstance(self.selected_fixture_odds, dict) else {}
        if isinstance(selected, dict) and selected:
            self.odds_card_home_value.config(text=str(selected.get("home", "-")))
            self.odds_card_draw_value.config(text=str(selected.get("draw", "-")))
            self.odds_card_away_value.config(text=str(selected.get("away", "-")))

    def _safe_ratio(self, a, b):
        total = max(1, a + b)
        return int((a / total) * 100)

    def _render_form_bar(self, canvas, left_value, right_value):
        canvas.delete("all")
        width = max(1, int(canvas.winfo_width() or 260))
        height = max(1, int(canvas.winfo_height() or 18))
        left_w = int(width * (left_value / 100))
        canvas.create_rectangle(0, 0, left_w, height, outline="", fill="#2563eb")
        canvas.create_rectangle(left_w, 0, width, height, outline="", fill="#dc2626")
        canvas.create_text(width // 2, height // 2, text=f"{left_value}% - {right_value}%", fill="white")

    # ------------------------------------------------
    # OTHER
    # ------------------------------------------------

    def open_transfer_market(self):
        win = tk.Toplevel(self.root)
        win.title("Transfer Market")
        win.geometry("560x430")

        box = tk.Text(win, bg="#09111f", fg="white")
        box.pack(fill="both", expand=True)

        box.insert("end", "Transfer market integration is ready.\n")
        box.insert("end", "This window can be connected to backend-backed player market data later.\n")

    def quit_app(self):
        if messagebox.askyesno("Quit", "Exit simulator?"):
            self.root.destroy()


if __name__ == "__main__":
    root = tk.Tk()
    app = FootballSimulator(root)
    root.mainloop()