import tkinter as tk
from tkinter import ttk, messagebox
import os

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

from sim_integration.backend_client import SimulatorDataClient
from sim_integration.tk_helpers import run_in_background


APP_VERSION = "v1.1.0"
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


class FootballSimulator:
    def __init__(self, root):
        self.root = root
        self.root.title("Football Match Simulator")
        self.root.geometry("1280x720")
        self.root.minsize(1100, 650)
        self.root.resizable(True, True)
        self.root.configure(bg="#0f172a")

        self.dark_mode = True
        self.match_duration_seconds = 60
        self.live_refresh_ms = 10 * 60 * 1000
        self.current_competition = os.getenv("DEFAULT_COMPETITION", "PL")

        self.home_score = 0
        self.away_score = 0
        self.match_time = 0
        self.match_finished = False

        self.audio_enabled = True
        self.show_tracker_lines = True
        self.show_player_labels = True
        self.fast_graphics = False

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
        self.logos = []
        self.backend_usage = {}
        self.export_status = {}
        self.live_games = {}
        self.odds_markets = {}
        self.bet365_prematch = {}
        self.tournament_odds = {}
        self.selected_fixture_odds = {}

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
        self.engine.frame_ms = 16

        self.startup_backend_then_load()
        self.update_clock()
        self.update_manager_tactics_loop()
        self.schedule_live_refresh_loop()

    # ------------------------------------------------
    # STARTUP / BACKEND
    # ------------------------------------------------

    def startup_backend_then_load(self):
        self.status_label.config(text="Checking backend...")
        self.add_commentary("Checking backend status...")
        run_in_background(
            self._ensure_backend_running,
            self._on_backend_ready,
            self._on_backend_error,
        )

    def _ensure_backend_running(self):
        if self.backend_launcher.is_backend_running():
            return {"started": False, "ready": True}
        started = self.backend_launcher.start_backend()
        return {"started": True, "ready": started}

    def _on_backend_ready(self, result):
        if result and result.get("ready"):
            if result.get("started"):
                self.add_commentary("Backend started automatically.")
                self.status_label.config(text="Backend started. Loading simulator data...")
            else:
                self.add_commentary("Backend already running.")
                self.status_label.config(text="Backend online. Loading simulator data...")
            self.load_initial_data()
        else:
            self.status_label.config(text="Backend did not start.")
            self.add_commentary("Backend could not be started automatically. Check backend files and VPN.")

    def _on_backend_error(self, error):
        self.status_label.config(text=f"Backend startup error: {error}")
        self.add_commentary("Backend startup failed.")

    # ------------------------------------------------
    # DATA
    # ------------------------------------------------

    def load_initial_data(self):
        self.status_label.config(text=f"Loading backend/cache data for {self.current_competition}...")
        self.add_commentary(f"Loading backend/cache data for {self.current_competition}...")
        run_in_background(
            self._fetch_all_data,
            self._on_data_loaded,
            self._on_data_error,
        )

    def _fetch_all_data(self):
        comp = self.current_competition
        return {
            "teams": self.data_client.load_teams(comp),
            "fixtures": self.data_client.load_fixtures(comp),
            "standings": self.data_client.load_standings(comp),
            "news": self.data_client.load_news(comp),
            "logos": self.data_client.load_logos(comp),
            "usage": self.data_client.load_usage(),
            "export_status": self.data_client.load_export_status(),
            "live_games": self.data_client.load_live_games(),
            "odds_markets": self.data_client.load_odds_markets(),
            "bet365_prematch": self.data_client.load_bet365_prematch(),
            "tournament_odds": self.data_client.load_odds_tournaments("17"),
        }

    def _on_data_loaded(self, data):
        if not data:
            self.status_label.config(text="No data returned. Using fallback state.")
            self.add_commentary("No backend/cache data returned.")
            return

        self.teams = data.get("teams", []) or []
        self.fixtures = data.get("fixtures", []) or []
        self.standings = data.get("standings", []) or []
        self.news_items = data.get("news", []) or []
        self.logos = data.get("logos", []) or []
        self.backend_usage = data.get("usage", {}) or {}
        self.export_status = data.get("export_status", {}) or {}
        self.live_games = data.get("live_games", {}) or {}
        self.odds_markets = data.get("odds_markets", {}) or {}
        self.bet365_prematch = data.get("bet365_prematch", {}) or {}
        self.tournament_odds = data.get("tournament_odds", {}) or {}

        self.team_list = sorted(
            {
                t.get("name", "").strip()
                for t in self.teams
                if isinstance(t, dict) and t.get("name")
            }
        )

        self.reload_selectors()
        self.reload_side_panels()
        self.refresh_sidebar_badges()
        self.refresh_match_detail_strip()

        used = self.backend_usage.get("used")
        limit_ = self.backend_usage.get("limit")
        remaining = self.backend_usage.get("remaining")

        if self.team_list:
            if used is not None and limit_ is not None:
                self.status_label.config(
                    text=f"{self.current_competition} ready | Teams: {len(self.team_list)} | Usage: {used}/{limit_} | Remaining: {remaining}"
                )
            else:
                self.status_label.config(text=f"{self.current_competition} ready | Teams: {len(self.team_list)}")
            self.add_commentary(f"Simulator data loaded for {self.current_competition}. Teams available: {len(self.team_list)}")
        else:
            self.status_label.config(text=f"No teams loaded for {self.current_competition}. Backend provider may be failing.")
            self.add_commentary(f"No teams loaded for {self.current_competition}. Backend provider may be failing.")

        self.show_export_summary()

    def _on_data_error(self, error):
        self.status_label.config(text=f"Data load error: {error}")
        self.add_commentary("Failed to refresh backend data; using whatever local cache is available.")

    def show_export_summary(self):
        files = self.export_status.get("files", []) if isinstance(self.export_status, dict) else []
        if not files:
            self.add_commentary("Export status unavailable.")
            return

        existing = [f["file"] for f in files if f.get("exists")]
        missing = [f["file"] for f in files if not f.get("exists")]

        if existing:
            self.add_commentary("Export files found: " + ", ".join(existing[:5]))
        if missing:
            self.add_commentary("Missing export files: " + ", ".join(missing[:5]))

    def schedule_live_refresh_loop(self):
        self.root.after(self.live_refresh_ms, self._live_refresh_wrapper)

    def _live_refresh_wrapper(self):
        self.status_label.config(text=f"Refreshing backend data for {self.current_competition}...")
        self.add_commentary(f"Refreshing backend/cache data for {self.current_competition}...")
        run_in_background(
            self._fetch_all_data,
            self._on_data_loaded,
            self._on_data_error,
        )
        self.schedule_live_refresh_loop()

    def reload_selectors(self):
        self.home_box["values"] = self.team_list
        self.away_box["values"] = self.team_list

        if len(self.team_list) >= 2:
            if not self.home_box.get() or self.home_box.get() not in self.team_list:
                self.home_box.set(self.team_list[0])
            if not self.away_box.get() or self.away_box.get() not in self.team_list:
                self.away_box.set(self.team_list[1])
        elif len(self.team_list) == 1:
            self.home_box.set(self.team_list[0])
            self.away_box.set(self.team_list[0])

    def refresh_sidebar_badges(self):
        home = self.home_box.get().strip()
        away = self.away_box.get().strip()

        self.home_sidebar_badge_img = self.logo_loader.load_size(home, "tiny") if home else None
        self.away_sidebar_badge_img = self.logo_loader.load_size(away, "tiny") if away else None

        if self.home_sidebar_badge_img:
            self.home_badge_sidebar.config(image=self.home_sidebar_badge_img, text="")
            self.home_badge_sidebar.image = self.home_sidebar_badge_img
        else:
            self.home_badge_sidebar.config(image="", text="No badge")

        if self.away_sidebar_badge_img:
            self.away_badge_sidebar.config(image=self.away_sidebar_badge_img, text="")
            self.away_badge_sidebar.image = self.away_sidebar_badge_img
        else:
            self.away_badge_sidebar.config(image="", text="No badge")

    def refresh_match_detail_strip(self):
        home = self.home_box.get().strip() or "Home"
        away = self.away_box.get().strip() or "Away"

        self.match_detail_label.config(text=f"{home} vs {away} | League: {self.current_competition}")

        odds_caption = self.prediction_engine.build_odds_caption(self.selected_fixture_odds)
        self.odds_caption_label.config(text=odds_caption)

        self.detail_home_badge_img = self.logo_loader.load_size(home, "tiny") if home else None
        self.detail_away_badge_img = self.logo_loader.load_size(away, "tiny") if away else None

        if self.detail_home_badge_img:
            self.detail_home_badge.config(image=self.detail_home_badge_img, text="")
            self.detail_home_badge.image = self.detail_home_badge_img
        else:
            self.detail_home_badge.config(image="", text="")

        if self.detail_away_badge_img:
            self.detail_away_badge.config(image=self.detail_away_badge_img, text="")
            self.detail_away_badge.image = self.detail_away_badge_img
        else:
            self.detail_away_badge.config(image="", text="")

    def _render_selected_odds(self):
        self.odds_card_home_value.config(text="-")
        self.odds_card_draw_value.config(text="-")
        self.odds_card_away_value.config(text="-")
        self.odds_card_match_label.config(text="Selected match odds unavailable")

        selected = self.selected_fixture_odds.get("selected", {}) if isinstance(self.selected_fixture_odds, dict) else {}
        if not isinstance(selected, dict) or not selected:
            self.refresh_match_detail_strip()
            return

        self.odds_card_match_label.config(
            text=f"{self.home_box.get().strip()} vs {self.away_box.get().strip()}"
        )
        self.odds_card_home_value.config(text=str(selected.get("home", "-")))
        self.odds_card_draw_value.config(text=str(selected.get("draw", "-")))
        self.odds_card_away_value.config(text=str(selected.get("away", "-")))
        self.refresh_match_detail_strip()

    def _team_priority_score(self, item_home: str, item_away: str, selected_home: str, selected_away: str) -> int:
        score = 0
        if selected_home and selected_home in (item_home, item_away):
            score += 2
        if selected_away and selected_away in (item_home, item_away):
            score += 2
        return score

    def _selected_fixtures_first(self):
        selected_home = self.home_box.get().strip()
        selected_away = self.away_box.get().strip()

        items = list(self.fixtures or [])
        items.sort(
            key=lambda r: (
                -self._team_priority_score(r.get("home", ""), r.get("away", ""), selected_home, selected_away),
                r.get("status", ""),
                r.get("utcDate", ""),
            )
        )
        return items

    def _selected_live_first(self):
        if not isinstance(self.live_games, dict):
            return [], [], []

        selected_home = self.home_box.get().strip()
        selected_away = self.away_box.get().strip()

        live_matches = list(self.live_games.get("live_matches", []) or [])
        scheduled = list(self.live_games.get("scheduled_with_odds", []) or [])
        errors = list(self.live_games.get("errors", []) or [])

        live_matches.sort(
            key=lambda m: -self._team_priority_score(m.get("home", ""), m.get("away", ""), selected_home, selected_away)
        )
        scheduled.sort(
            key=lambda m: -self._team_priority_score(m.get("home", ""), m.get("away", ""), selected_home, selected_away)
        )

        return live_matches, scheduled, errors

    def _format_fixture_line(self, home: str, away: str, status: str) -> str:
        return f"• {home} vs {away}   {status}"

    def _format_live_line(self, home: str, away: str, sh, sa, minute: str, status: str) -> str:
        return f"• {home} {sh}-{sa} {away}   {minute} {status}"

    def reload_side_panels(self):
        for box in (self.table_box, self.fixtures_box, self.live_box, self.odds_box, self.news_box):
            box.delete("1.0", "end")

        self._render_selected_odds()

        if self.standings:
            for row in self.standings[:20]:
                self.table_box.insert("end", f"{row.get('team','')}  P:{row.get('played',0)}  Pts:{row.get('points',0)}\n")
        else:
            self.table_box.insert("end", "No standings loaded.\n")

        prioritized_fixtures = self._selected_fixtures_first()
        if prioritized_fixtures:
            selected_home = self.home_box.get().strip()
            selected_away = self.away_box.get().strip()

            self.fixtures_box.insert("end", "SELECTED TEAMS FIRST\n")
            for row in prioritized_fixtures[:20]:
                prefix = "★ " if self._team_priority_score(
                    row.get("home", ""), row.get("away", ""), selected_home, selected_away
                ) > 0 else "• "
                self.fixtures_box.insert(
                    "end",
                    f"{prefix}{row.get('home','')} vs {row.get('away','')}   {row.get('status','')}\n"
                )
        else:
            self.fixtures_box.insert("end", "No fixtures loaded.\n")

        live_matches, scheduled, errors = self._selected_live_first()

        if live_matches:
            self.live_box.insert("end", "LIVE MATCHES\n")
            selected_home = self.home_box.get().strip()
            selected_away = self.away_box.get().strip()

            for m in live_matches[:12]:
                prefix = "★ " if self._team_priority_score(
                    m.get("home", ""), m.get("away", ""), selected_home, selected_away
                ) > 0 else "• "
                self.live_box.insert(
                    "end",
                    f"{prefix}{m.get('home','')} {m.get('score_home','?')}-{m.get('score_away','?')} {m.get('away','')}   {m.get('minute','')} {m.get('status','LIVE')}\n"
                )

        elif scheduled:
            self.live_box.insert("end", "UPCOMING WITH ODDS\n")
            selected_home = self.home_box.get().strip()
            selected_away = self.away_box.get().strip()

            for m in scheduled[:12]:
                prefix = "★ " if self._team_priority_score(
                    m.get("home", ""), m.get("away", ""), selected_home, selected_away
                ) > 0 else "• "
                self.live_box.insert(
                    "end",
                    f"{prefix}{m.get('home','')} vs {m.get('away','')}   {m.get('status','')}   {m.get('start_time','')}\n"
                )
        else:
            self.live_box.insert("end", "No live games loaded yet.\n")

        if errors:
            self.live_box.insert("end", "\nErrors:\n")
            for err in errors[:4]:
                self.live_box.insert("end", f"- {err}\n")

        self.odds_box.insert("end", "ODDS SUMMARY\n")

        if isinstance(self.bet365_prematch, dict):
            summary = self.bet365_prematch.get("summary", {}) or {}
            self.odds_box.insert("end", f"Bet365 prematch events: {summary.get('event_count', 0)}\n")

        if isinstance(self.odds_markets, dict):
            self.odds_box.insert("end", f"Available markets: {self.odds_markets.get('market_count', 0)}\n")

        if isinstance(self.tournament_odds, dict):
            summary = self.tournament_odds.get("summary", {}) or {}
            self.odds_box.insert("end", f"Tournament odds items: {summary.get('item_count', 0)}\n")

        selected = self.selected_fixture_odds.get("selected", {}) if isinstance(self.selected_fixture_odds, dict) else {}
        if isinstance(selected, dict) and selected:
            self.odds_box.insert(
                "end",
                f"Selected 1X2: H:{selected.get('home','-')} D:{selected.get('draw','-')} A:{selected.get('away','-')}\n"
            )
        else:
            self.odds_box.insert("end", "Selected 1X2: unavailable\n")

        if self.news_items:
            for row in self.news_items[:20]:
                self.news_box.insert("end", f"{row.get('title','')}\n{row.get('summary','')}\n\n")
        else:
            self.news_box.insert("end", "No news loaded.\n")

    def _league_name_from_code(self, code):
        for name, value in LEAGUE_OPTIONS.items():
            if value == code:
                return name
        return "Premier League"

    # ------------------------------------------------
    # UI
    # ------------------------------------------------

    def build_ui(self):
        self.outer = tk.Frame(self.root, bg="#0f172a")
        self.outer.pack(fill="both", expand=True)

        self.app_canvas = tk.Canvas(self.outer, bg="#0f172a", highlightthickness=0)
        self.app_canvas.pack(side="left", fill="both", expand=True)

        self.v_scroll = tk.Scrollbar(self.outer, orient="vertical", command=self.app_canvas.yview)
        self.v_scroll.pack(side="right", fill="y")

        self.h_scroll = tk.Scrollbar(self.root, orient="horizontal", command=self.app_canvas.xview)
        self.h_scroll.pack(side="bottom", fill="x")

        self.app_canvas.configure(yscrollcommand=self.v_scroll.set, xscrollcommand=self.h_scroll.set)

        self.main = tk.Frame(self.app_canvas, bg="#0f172a")
        self.canvas_window = self.app_canvas.create_window((0, 0), window=self.main, anchor="nw")

        self.main.bind("<Configure>", self.on_main_configure)
        self.app_canvas.bind("<Configure>", self.on_canvas_configure)

        self.app_canvas.bind_all("<MouseWheel>", self.on_mousewheel)
        self.app_canvas.bind_all("<Shift-MouseWheel>", self.on_shift_mousewheel)
        self.root.bind_all("<Up>", lambda e: self.app_canvas.yview_scroll(-1, "units"))
        self.root.bind_all("<Down>", lambda e: self.app_canvas.yview_scroll(1, "units"))
        self.root.bind_all("<Left>", lambda e: self.app_canvas.xview_scroll(-1, "units"))
        self.root.bind_all("<Right>", lambda e: self.app_canvas.xview_scroll(1, "units"))
        self.app_canvas.bind("<ButtonPress-1>", self.start_pan)
        self.app_canvas.bind("<B1-Motion>", self.do_pan)

        self.build_header()

        self.page_nav = tk.Frame(self.main, bg="#14213d")
        self.page_nav.pack(fill="x", pady=(0, 4))

        tk.Button(self.page_nav, text="Match", command=lambda: self.show_page("match"), bg="#1b3a5a", fg="white").pack(side="left", padx=4, pady=4)
        tk.Button(self.page_nav, text="Settings", command=lambda: self.show_page("settings"), bg="#1b3a5a", fg="white").pack(side="left", padx=4, pady=4)

        self.match_page = tk.Frame(self.main, bg="#0f172a")
        self.settings_page = tk.Frame(self.main, bg="#0f172a")

        self.build_match_page()
        self.build_settings_page()
        self.show_page("match")

    def on_main_configure(self, _event=None):
        self.app_canvas.configure(scrollregion=self.app_canvas.bbox("all"))

    def on_canvas_configure(self, event):
        self.app_canvas.itemconfig(self.canvas_window, width=max(event.width, 1280))
        self.app_canvas.configure(scrollregion=self.app_canvas.bbox("all"))

    def on_mousewheel(self, event):
        self.app_canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

    def on_shift_mousewheel(self, event):
        self.app_canvas.xview_scroll(int(-1 * (event.delta / 120)), "units")

    def start_pan(self, event):
        self.app_canvas.scan_mark(event.x, event.y)

    def do_pan(self, event):
        self.app_canvas.scan_dragto(event.x, event.y, gain=1)

    def show_page(self, page_name):
        self.match_page.pack_forget()
        self.settings_page.pack_forget()
        if page_name == "settings":
            self.settings_page.pack(fill="both", expand=True)
        else:
            self.match_page.pack(fill="both", expand=True)

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

        self.prediction_label = tk.Label(
            self.header,
            text="Prediction: waiting",
            bg="#1e293b",
            fg="#ffd166",
            font=("Arial", 11, "bold"),
            wraplength=420,
            justify="left"
        )
        self.prediction_label.pack(side="left", padx=10)

        self.clock_label = tk.Label(self.header, text="00:00", bg="#1e293b", fg="white", font=("Arial", 20))
        self.clock_label.pack(side="right", padx=20)

        self.possession_label = tk.Label(self.header, text="Possession 50% - 50%", bg="#1e293b", fg="white", font=("Arial", 12))
        self.possession_label.pack(side="right", padx=20)

    def build_match_page(self):
        body = tk.Frame(self.match_page, bg="#0f172a")
        body.pack(fill="both", expand=True)

        detail_strip = tk.Frame(self.match_page, bg="#111827")
        detail_strip.pack(fill="x", pady=(0, 2))

        self.detail_home_badge = tk.Label(detail_strip, bg="#111827")
        self.detail_home_badge.pack(side="left", padx=(8, 4), pady=4)

        self.match_detail_label = tk.Label(
            detail_strip,
            text="Home vs Away | League: PL",
            bg="#111827",
            fg="#e5e7eb",
            font=("Arial", 10, "bold"),
            anchor="w"
        )
        self.match_detail_label.pack(side="left", padx=6, pady=4)

        self.detail_away_badge = tk.Label(detail_strip, bg="#111827")
        self.detail_away_badge.pack(side="left", padx=(4, 8), pady=4)

        self.odds_caption_label = tk.Label(
            detail_strip,
            text="Odds: unavailable",
            bg="#111827",
            fg="#93c5fd",
            font=("Arial", 10),
            anchor="e"
        )
        self.odds_caption_label.pack(side="right", padx=10, pady=4)

        self.build_sidebar(body)
        self.build_pitch(body)
        self.build_right_panel(body)
        self.build_footer()

    def build_sidebar(self, parent):
        self.sidebar = tk.Frame(parent, bg="#0b2545", width=300)
        self.sidebar.pack(side="left", fill="y")

        tk.Label(self.sidebar, text="League", bg="#0b2545", fg="white").pack(pady=(16, 6))
        self.league_box = ttk.Combobox(self.sidebar, values=list(LEAGUE_OPTIONS.keys()), state="readonly")
        self.league_box.pack(padx=12, fill="x")
        self.league_box.set(self._league_name_from_code(self.current_competition))
        self.league_box.bind("<<ComboboxSelected>>", self.on_league_changed)

        tk.Label(self.sidebar, text="Home Team", bg="#0b2545", fg="white").pack(pady=(16, 6))
        home_row = tk.Frame(self.sidebar, bg="#0b2545")
        home_row.pack(padx=12, fill="x")
        self.home_badge_sidebar = tk.Label(home_row, bg="#0b2545", fg="white", width=8, anchor="w")
        self.home_badge_sidebar.pack(side="left")
        self.home_box = ttk.Combobox(home_row, values=self.team_list, height=20, state="normal")
        self.home_box.pack(side="left", fill="x", expand=True)
        self.home_box.bind("<<ComboboxSelected>>", self.on_team_selection_changed)

        tk.Label(self.sidebar, text="Away Team", bg="#0b2545", fg="white").pack(pady=(16, 6))
        away_row = tk.Frame(self.sidebar, bg="#0b2545")
        away_row.pack(padx=12, fill="x")
        self.away_badge_sidebar = tk.Label(away_row, bg="#0b2545", fg="white", width=8, anchor="w")
        self.away_badge_sidebar.pack(side="left")
        self.away_box = ttk.Combobox(away_row, values=self.team_list, height=20, state="normal")
        self.away_box.pack(side="left", fill="x", expand=True)
        self.away_box.bind("<<ComboboxSelected>>", self.on_team_selection_changed)

        formation_values = ["4-3-3", "4-2-3-1", "4-4-2", "3-5-2"]

        tk.Label(self.sidebar, text="Home Formation", bg="#0b2545", fg="white").pack(pady=(16, 6))
        self.home_formation_box = ttk.Combobox(self.sidebar, values=formation_values, state="readonly")
        self.home_formation_box.pack(padx=12, fill="x")

        tk.Label(self.sidebar, text="Away Formation", bg="#0b2545", fg="white").pack(pady=(16, 6))
        self.away_formation_box = ttk.Combobox(self.sidebar, values=formation_values, state="readonly")
        self.away_formation_box.pack(padx=12, fill="x")

        self.home_formation_box.set("4-3-3")
        self.away_formation_box.set("4-2-3-1")

        btn_cfg = {"width": 22, "bg": "#1b3a5a", "fg": "white", "activebackground": "#31577c"}

        tk.Button(self.sidebar, text="▶ Start Match", command=self.start_match, **btn_cfg).pack(pady=(20, 6))
        tk.Button(self.sidebar, text="⏸ Pause Match", command=self.pause_match, **btn_cfg).pack(pady=6)
        tk.Button(self.sidebar, text="🔄 Reset Match", command=self.reset_match, **btn_cfg).pack(pady=6)
        tk.Button(self.sidebar, text="🔃 Refresh Live Data", command=self.load_initial_data, **btn_cfg).pack(pady=6)
        tk.Button(self.sidebar, text="💰 Transfer Market", command=self.open_transfer_market, **btn_cfg).pack(pady=6)
        tk.Button(self.sidebar, text="⚙ Settings", command=lambda: self.show_page("settings"), **btn_cfg).pack(pady=6)
        tk.Button(self.sidebar, text="❌ Quit", command=self.quit_app, **btn_cfg).pack(pady=6)

        self.tactic_label = tk.Label(self.sidebar, text="Live tactics: waiting", bg="#0b2545", fg="#cbd5e1", justify="left", wraplength=250)
        self.tactic_label.pack(pady=(18, 6), padx=12)

        self.form_label = tk.Label(self.sidebar, text="Team form: waiting", bg="#0b2545", fg="#93c5fd", justify="left", wraplength=250)
        self.form_label.pack(pady=(8, 6), padx=12)

    def on_league_changed(self, _event=None):
        selected = self.league_box.get()
        code = LEAGUE_OPTIONS.get(selected, "PL")
        self.current_competition = code
        self.add_commentary(f"League changed to {selected} ({code}). Refreshing data...")
        self.load_initial_data()

    def on_team_selection_changed(self, _event=None):
        self.refresh_sidebar_badges()
        self.refresh_match_detail_strip()

        home = self.home_box.get().strip()
        away = self.away_box.get().strip()
        if home and away and home != away:
            run_in_background(
                lambda: self.data_client.load_selected_fixture_odds(home, away),
                self._on_selected_fixture_odds_loaded,
                self._on_data_error,
            )

    def _on_selected_fixture_odds_loaded(self, data):
        self.selected_fixture_odds = data or {}
        self.reload_side_panels()
        self.refresh_match_detail_strip()

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
        self.canvas.pack(expand=True, pady=26, padx=10)

    def build_right_panel(self, parent):
        self.right_panel = tk.Frame(parent, bg="#0b2545", width=390)
        self.right_panel.pack(side="right", fill="both")

        self.right_canvas = tk.Canvas(self.right_panel, bg="#0b2545", highlightthickness=0, width=390)
        self.right_scroll = tk.Scrollbar(self.right_panel, orient="vertical", command=self.right_canvas.yview)
        self.right_inner = tk.Frame(self.right_canvas, bg="#0b2545")

        self.right_inner.bind(
            "<Configure>",
            lambda e: self.right_canvas.configure(scrollregion=self.right_canvas.bbox("all"))
        )

        self.right_canvas.create_window((0, 0), window=self.right_inner, anchor="nw")
        self.right_canvas.configure(yscrollcommand=self.right_scroll.set)

        self.right_canvas.pack(side="left", fill="both", expand=True)
        self.right_scroll.pack(side="right", fill="y")

        self.odds_card = tk.LabelFrame(
            self.right_inner,
            text="Selected Match Odds",
            bg="#0b2545",
            fg="white",
            padx=10,
            pady=10
        )
        self.odds_card.pack(fill="x", padx=10, pady=(10, 8))

        self.odds_card_match_label = tk.Label(
            self.odds_card,
            text="Selected match odds unavailable",
            bg="#0b2545",
            fg="#e2e8f0",
            font=("Arial", 10, "bold"),
            anchor="w",
            justify="left"
        )
        self.odds_card_match_label.pack(fill="x", pady=(0, 8))

        values_row = tk.Frame(self.odds_card, bg="#0b2545")
        values_row.pack(fill="x")

        self._build_odds_value_box(values_row, "HOME", "odds_card_home_value")
        self._build_odds_value_box(values_row, "DRAW", "odds_card_draw_value")
        self._build_odds_value_box(values_row, "AWAY", "odds_card_away_value")

        tk.Label(self.right_inner, text="Match Statistics", bg="#0b2545", fg="white", font=("Arial", 12, "bold")).pack(pady=10)
        self.stats_box = tk.Text(self.right_inner, height=8, width=44, bg="#091c34", fg="white")
        self.stats_box.pack(padx=10)

        tk.Label(self.right_inner, text="Event Timeline", bg="#0b2545", fg="white", font=("Arial", 12, "bold")).pack(pady=10)
        self.timeline_box = tk.Text(self.right_inner, height=8, width=44, bg="#091c34", fg="white")
        self.timeline_box.pack(padx=10)

        tk.Label(self.right_inner, text="League Table", bg="#0b2545", fg="white", font=("Arial", 12, "bold")).pack(pady=10)
        self.table_box = tk.Text(self.right_inner, height=8, width=44, bg="#091c34", fg="white")
        self.table_box.pack(padx=10)

        tk.Label(self.right_inner, text="Fixtures", bg="#0b2545", fg="white", font=("Arial", 12, "bold")).pack(pady=10)
        self.fixtures_box = tk.Text(self.right_inner, height=6, width=44, bg="#091c34", fg="white")
        self.fixtures_box.pack(padx=10)

        tk.Label(self.right_inner, text="Live Games", bg="#0b2545", fg="white", font=("Arial", 12, "bold")).pack(pady=10)
        self.live_box = tk.Text(self.right_inner, height=6, width=44, bg="#091c34", fg="white")
        self.live_box.pack(padx=10)

        tk.Label(self.right_inner, text="Odds Summary", bg="#0b2545", fg="white", font=("Arial", 12, "bold")).pack(pady=10)
        self.odds_box = tk.Text(self.right_inner, height=8, width=44, bg="#091c34", fg="white")
        self.odds_box.pack(padx=10)

        tk.Label(self.right_inner, text="Club News", bg="#0b2545", fg="white", font=("Arial", 12, "bold")).pack(pady=10)
        self.news_box = tk.Text(self.right_inner, height=6, width=44, bg="#091c34", fg="white")
        self.news_box.pack(padx=10)

    def _build_odds_value_box(self, parent, title, value_attr_name):
        box = tk.Frame(parent, bg="#091c34", padx=10, pady=8)
        box.pack(side="left", expand=True, fill="both", padx=4)

        tk.Label(box, text=title, bg="#091c34", fg="#93c5fd", font=("Arial", 9, "bold")).pack()
        value_label = tk.Label(box, text="-", bg="#091c34", fg="white", font=("Arial", 14, "bold"))
        value_label.pack()
        setattr(self, value_attr_name, value_label)

    def build_footer(self):
        footer = tk.Frame(self.match_page, bg="#020617")
        footer.pack(fill="x")

        self.commentary_box = tk.Text(footer, height=7, bg="#020617", fg="white")
        self.commentary_box.pack(fill="x")

        self.status_label = tk.Label(footer, text="Ready", bg="#020617", fg="#94a3b8", anchor="w")
        self.status_label.pack(fill="x", padx=8, pady=4)

    def build_settings_page(self):
        frame = self.settings_page

        title = tk.Label(frame, text="Settings", font=("Arial", 22, "bold"), bg="#0f172a", fg="white")
        title.pack(pady=16)

        content = tk.Frame(frame, bg="#0f172a")
        content.pack(fill="both", expand=True, padx=20, pady=10)

        visual_card = tk.LabelFrame(content, text="Visual Settings", bg="#0b2545", fg="white", padx=12, pady=12)
        visual_card.pack(fill="x", pady=8)

        tk.Button(visual_card, text="Toggle Dark / Light", command=self.toggle_theme, bg="#1b3a5a", fg="white").pack(anchor="w", pady=4)
        tk.Button(visual_card, text="Toggle Player Labels", command=self.toggle_player_labels, bg="#1b3a5a", fg="white").pack(anchor="w", pady=4)
        tk.Button(visual_card, text="Toggle Tracker Lines", command=self.toggle_tracker_lines, bg="#1b3a5a", fg="white").pack(anchor="w", pady=4)

        league_card = tk.LabelFrame(content, text="League Settings", bg="#0b2545", fg="white", padx=12, pady=12)
        league_card.pack(fill="x", pady=8)

        tk.Label(league_card, text="Default league", bg="#0b2545", fg="white").pack(anchor="w")
        self.settings_league_box = ttk.Combobox(league_card, values=list(LEAGUE_OPTIONS.keys()), state="readonly")
        self.settings_league_box.pack(fill="x", pady=6)
        self.settings_league_box.set(self._league_name_from_code(self.current_competition))
        self.settings_league_box.bind("<<ComboboxSelected>>", self.on_settings_league_changed)

        game_card = tk.LabelFrame(content, text="Game Settings", bg="#0b2545", fg="white", padx=12, pady=12)
        game_card.pack(fill="x", pady=8)

        tk.Button(game_card, text="Match Duration = 60s", command=lambda: self.set_match_duration(60), bg="#1b3a5a", fg="white").pack(anchor="w", pady=4)
        tk.Button(game_card, text="Match Duration = 30s", command=lambda: self.set_match_duration(30), bg="#1b3a5a", fg="white").pack(anchor="w", pady=4)
        tk.Button(game_card, text="Live Refresh = 10 min", command=lambda: self.set_live_refresh(10), bg="#1b3a5a", fg="white").pack(anchor="w", pady=4)
        tk.Button(game_card, text="Live Refresh = 15 min", command=lambda: self.set_live_refresh(15), bg="#1b3a5a", fg="white").pack(anchor="w", pady=4)

        audio_card = tk.LabelFrame(content, text="Audio Settings", bg="#0b2545", fg="white", padx=12, pady=12)
        audio_card.pack(fill="x", pady=8)

        tk.Button(audio_card, text="Mute / Unmute Crowd", command=self.toggle_mute, bg="#1b3a5a", fg="white").pack(anchor="w", pady=4)

        gfx_card = tk.LabelFrame(content, text="Graphics Settings", bg="#0b2545", fg="white", padx=12, pady=12)
        gfx_card.pack(fill="x", pady=8)

        tk.Button(gfx_card, text="Normal Graphics", command=lambda: self.set_graphics_mode(False), bg="#1b3a5a", fg="white").pack(anchor="w", pady=4)
        tk.Button(gfx_card, text="Fast Graphics", command=lambda: self.set_graphics_mode(True), bg="#1b3a5a", fg="white").pack(anchor="w", pady=4)

        about_card = tk.LabelFrame(content, text="About", bg="#0b2545", fg="white", padx=12, pady=12)
        about_card.pack(fill="x", pady=8)

        about_text = (
            f"Football Match Simulator\n"
            f"Version: {APP_VERSION}\n"
            f"{APP_COPYRIGHT}\n"
            f"Architecture: Simulator → backend → providers"
        )
        tk.Label(about_card, text=about_text, justify="left", bg="#0b2545", fg="white").pack(anchor="w")

        tk.Button(frame, text="Back to Match", command=lambda: self.show_page("match"), bg="#1b3a5a", fg="white").pack(pady=12)

    def on_settings_league_changed(self, _event=None):
        selected = self.settings_league_box.get()
        code = LEAGUE_OPTIONS.get(selected, "PL")
        self.current_competition = code
        self.league_box.set(selected)
        self.add_commentary(f"League changed from settings to {selected} ({code}). Refreshing data...")
        self.load_initial_data()

    # ------------------------------------------------
    # MATCH CONTROL
    # ------------------------------------------------

    def load_header_logos(self, home, away):
        home_logo = self.logo_loader.load(home, small=True)
        away_logo = self.logo_loader.load(away, small=True)

        if home_logo is not None:
            self.home_logo_label.config(image=home_logo)
            self.home_logo_label.image = home_logo
        else:
            self.home_logo_label.config(image="", text="")

        if away_logo is not None:
            self.away_logo_label.config(image=away_logo)
            self.away_logo_label.image = away_logo
        else:
            self.away_logo_label.config(image="", text="")

    def start_match(self):
        home = self.home_box.get().strip()
        away = self.away_box.get().strip()
        home_form = self.home_formation_box.get().strip()
        away_form = self.away_formation_box.get().strip()

        if not self.team_list:
            self.add_commentary("No teams available. Fix backend provider keys or cache export first.")
            self.status_label.config(text="Cannot start match: no teams loaded")
            return

        if not home or not away:
            self.add_commentary("Please select both teams.")
            return

        self.timeline_engine.clear()
        self.timeline_box.delete("1.0", "end")
        self.form_label.config(text="Team form: loading...")
        self.status_label.config(text="Preparing match...")

        self.home_name_label.config(text=home)
        self.away_name_label.config(text=away)
        self.load_header_logos(home, away)
        self.refresh_match_detail_strip()

        self.home_score = 0
        self.away_score = 0
        self.match_time = 0
        self.match_finished = False

        self.score_label.config(text="0 - 0")
        self.clock_label.config(text="00:00")

        self.engine.configure_match(home, away, home_form, away_form)
        self.engine.frame_ms = 30 if self.fast_graphics else 16

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

    def _apply_pre_match_data(self, home, away, result):
        home_form = result.get("home_form", {}) if result else {}
        away_form = result.get("away_form", {}) if result else {}
        self.selected_fixture_odds = result.get("selected_fixture_odds", {}) if result else {}

        prediction_text = self.prediction_engine.build_prediction(
            home=home,
            away=away,
            home_form=home_form,
            away_form=away_form,
            live_games=self.live_games,
            prematch_summary=self.bet365_prematch,
            tournament_odds=self.tournament_odds,
            fixture_odds=self.selected_fixture_odds,
        )

        self.prediction_label.config(text=prediction_text)
        self.add_commentary(prediction_text)

        self.form_label.config(
            text=(
                f"Team form\n"
                f"{home}: {' '.join(home_form.get('form_last5', [])) or 'n/a'}\n"
                f"{away}: {' '.join(away_form.get('form_last5', [])) or 'n/a'}"
            )
        )

        self.reload_side_panels()
        self.refresh_match_detail_strip()
        self.status_label.config(text="Match started")

    def pause_match(self):
        self.engine.running = False
        self.add_commentary("Match paused.")
        self.status_label.config(text="Match paused")

    def reset_match(self):
        self.engine.reset_match()
        self.engine.running = False
        self.timeline_engine.clear()

        self.home_score = 0
        self.away_score = 0
        self.match_time = 0
        self.match_finished = False
        self.selected_fixture_odds = {}

        self.clock_label.config(text="00:00")
        self.score_label.config(text="0 - 0")
        self.possession_label.config(text="Possession 50% - 50%")
        self.prediction_label.config(text="Prediction: waiting")
        self.stats_box.delete("1.0", "end")
        self.timeline_box.delete("1.0", "end")
        self.tactic_label.config(text="Live tactics: waiting")
        self.form_label.config(text="Team form: waiting")
        self.status_label.config(text="Match reset")
        self.reload_side_panels()
        self.refresh_match_detail_strip()

        self.add_commentary("Match reset.")

    def open_transfer_market(self):
        win = tk.Toplevel(self.root)
        win.title("Transfer Market")
        win.geometry("560x430")

        box = tk.Text(win, bg="#091c34", fg="white")
        box.pack(fill="both", expand=True)

        box.insert("end", "Transfer market integration is ready.\n")
        box.insert("end", "This window can be connected to backend-backed player market data later.\n")

    # ------------------------------------------------
    # LIVE TACTICS
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

    # ------------------------------------------------
    # EVENTS / UPDATES
    # ------------------------------------------------

    def add_timeline_event(self, minute, kind, text):
        self.timeline_engine.add_event(minute, kind, text)
        self.timeline_box.delete("1.0", "end")
        for line in self.timeline_engine.as_lines(limit=24):
            self.timeline_box.insert("end", line + "\n")

    def goal_scored(self, team):
        if team == "home":
            self.home_score += 1
        else:
            self.away_score += 1

        self.audio.play_goal()
        self.score_label.config(text=f"{self.home_score} - {self.away_score}")
        self.add_commentary(self.commentary_engine.goal_commentary())

        minute = max(1, self.match_time)
        side = self.home_name_label.cget("text") if team == "home" else self.away_name_label.cget("text")
        self.add_timeline_event(minute, "goal", f"Goal for {side}")

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
        if lines > 240:
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

        post_text = f"Post-match model: {home} {self.home_score}-{self.away_score} {away}"
        self.prediction_label.config(text=post_text)
        self.add_commentary(post_text)
        self.status_label.config(text="Match finished")

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
    # SETTINGS
    # ------------------------------------------------

    def set_match_duration(self, secs):
        self.match_duration_seconds = secs
        self.add_commentary(f"Match duration set to {secs} seconds.")

    def set_live_refresh(self, mins):
        self.live_refresh_ms = mins * 60 * 1000
        self.add_commentary(f"Live data refresh set to every {mins} minutes.")

    def toggle_theme(self):
        self.dark_mode = not self.dark_mode
        bg = "#0f172a" if self.dark_mode else "#dbe4ee"

        self.root.configure(bg=bg)
        self.main.configure(bg=bg)
        self.match_page.configure(bg=bg)
        self.settings_page.configure(bg=bg)

    def toggle_mute(self):
        self.audio_enabled = not self.audio_enabled
        self.audio.set_muted(not self.audio_enabled)

    def toggle_player_labels(self):
        self.show_player_labels = not self.show_player_labels
        self.add_commentary(f"Player labels {'ON' if self.show_player_labels else 'OFF'}.")

    def toggle_tracker_lines(self):
        self.show_tracker_lines = not self.show_tracker_lines
        self.add_commentary(f"Tracker lines {'ON' if self.show_tracker_lines else 'OFF'}.")

    def set_graphics_mode(self, fast_mode):
        self.fast_graphics = fast_mode
        self.add_commentary("Fast graphics enabled." if fast_mode else "Normal graphics enabled.")

    def quit_app(self):
        if messagebox.askyesno("Quit", "Exit simulator?"):
            self.root.destroy()


if __name__ == "__main__":
    root = tk.Tk()
    app = FootballSimulator(root)
    root.mainloop()