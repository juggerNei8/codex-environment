from __future__ import annotations

import json
import os
import random
import threading
import time
import urllib.error
import urllib.request
from pathlib import Path
import tkinter as tk
from tkinter import ttk, messagebox, filedialog

import websocket

try:
    from PIL import Image, ImageTk
except Exception:
    Image = None
    ImageTk = None

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

APP_VERSION = "v1.5.3"
APP_COPYRIGHT = "© 2026 JuggerNei8 Football Simulator"

TRACKING_HTTP_BASE_URL = "http://127.0.0.1:8000"
TRACKING_WS_BASE_URL = "ws://127.0.0.1:8000"
DEFAULT_TRACKING_MATCH_ID = "video_demo"

TRACKING_STATUS_POLL_MS = 15000
TRACKING_MIN_HTTP_REFRESH_SECONDS = 8.0
TRACKING_HTTP_TIMEOUT_SECONDS = 5.0

SIMVISION_PROJECT_ROOT = Path(r"C:\Project X\simvision_api")

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


class EmbeddedTrackingWebSocketClient:
    def __init__(
        self,
        ws_base_url: str,
        match_id: str,
        on_message=None,
        on_status=None,
        reconnect_delay: float = 3.0,
    ):
        self.ws_base_url = ws_base_url.rstrip("/")
        self.match_id = match_id
        self.on_message = on_message
        self.on_status = on_status
        self.reconnect_delay = reconnect_delay

        self.ws = None
        self.thread = None
        self._stop_event = threading.Event()
        self._connected = False

    def _notify_status(self, status: str):
        if self.on_status:
            try:
                self.on_status(status)
            except Exception as exc:
                print(f"[tracking-ws-status-error] {exc}")

    def _build_url(self) -> str:
        return f"{self.ws_base_url}/realtime/ws/{self.match_id}"

    def _on_open(self, ws):
        self._connected = True
        self._notify_status("connected")

    def _on_message(self, ws, message):
        try:
            payload = json.loads(message)
        except json.JSONDecodeError:
            payload = {"type": "raw_message", "message": message}

        if self.on_message:
            try:
                self.on_message(payload)
            except Exception as exc:
                print(f"[tracking-ws-message-error] {exc}")

    def _on_error(self, ws, error):
        self._connected = False
        self._notify_status(f"error: {error}")

    def _on_close(self, ws, close_status_code, close_msg):
        self._connected = False
        self._notify_status(f"closed: code={close_status_code}, message={close_msg}")

    def _run_forever(self):
        while not self._stop_event.is_set():
            try:
                self._notify_status(f"connecting -> {self._build_url()}")
                self.ws = websocket.WebSocketApp(
                    self._build_url(),
                    on_open=self._on_open,
                    on_message=self._on_message,
                    on_error=self._on_error,
                    on_close=self._on_close,
                )
                self.ws.run_forever()
            except Exception as exc:
                self._notify_status(f"connection exception: {exc}")

            if not self._stop_event.is_set():
                self._notify_status(f"reconnecting in {self.reconnect_delay:.0f}s")
                time.sleep(self.reconnect_delay)

    def start(self):
        if self.thread and self.thread.is_alive():
            self._notify_status("already running")
            return
        self._stop_event.clear()
        self.thread = threading.Thread(target=self._run_forever, daemon=True)
        self.thread.start()
        self._notify_status("background listener started")

    def stop(self):
        self._stop_event.set()
        if self.ws:
            try:
                self.ws.close()
            except Exception as exc:
                self._notify_status(f"close error: {exc}")
        self._notify_status("stopped")

    @property
    def is_connected(self) -> bool:
        return self._connected


class TrackingArtifactBridge:
    def __init__(self, project_root: str | Path, match_id: str):
        self.project_root = Path(project_root)
        self.match_id = match_id
        self.job_dir = self.project_root / "outputs" / "video" / "jobs" / self.match_id

    @property
    def tracking_output_path(self) -> Path:
        return self.job_dir / "tracking_output.json"

    @property
    def pitch_map_path(self) -> Path:
        return self.job_dir / "pitch_map.json"

    @property
    def calibration_points_path(self) -> Path:
        return self.job_dir / "calibration_points.json"

    @property
    def calibration_preview_path(self) -> Path:
        return self.job_dir / "calibration_preview.jpg"

    @property
    def frames_dir(self) -> Path:
        return self.job_dir / "frames"

    def _read_json(self, path: Path):
        if not path.exists():
            return {}
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            return {}

    def frames_exported(self) -> int:
        if not self.frames_dir.exists():
            return 0
        return len(list(self.frames_dir.glob("frame_*.jpg")))

    def tracking_summary(self):
        payload = self._read_json(self.tracking_output_path)
        if not payload:
            return {
                "available": False,
                "processor": "unknown",
                "status": "missing",
                "frames_processed": 0,
                "player_tracks": 0,
                "ball_tracks": 0,
                "home_team_tracks": 0,
                "away_team_tracks": 0,
                "official_tracks": 0,
                "goalkeeper_candidates": 0,
            }
        return {
            "available": True,
            "processor": payload.get("processor", "unknown"),
            "status": payload.get("status", "unknown"),
            "frames_processed": payload.get("frames_processed", 0),
            "player_tracks": payload.get("player_tracks", 0),
            "ball_tracks": payload.get("ball_tracks", 0),
            "home_team_tracks": payload.get("home_team_tracks", 0),
            "away_team_tracks": payload.get("away_team_tracks", 0),
            "official_tracks": payload.get("official_tracks", 0),
            "goalkeeper_candidates": payload.get("goalkeeper_candidates", 0),
        }

    def pitch_summary(self):
        payload = self._read_json(self.pitch_map_path)
        if not payload:
            return {
                "available": False,
                "method": "unknown",
                "calibration_used": False,
                "mapped_points": 0,
                "orientation_confidence": 0.0,
            }
        return {
            "available": True,
            "method": payload.get("method", "unknown"),
            "calibration_used": payload.get("calibration_used", False),
            "mapped_points": payload.get("mapped_points", 0),
            "orientation_confidence": payload.get("orientation", {}).get("confidence", 0.0),
        }

    def calibration_summary(self):
        payload = self._read_json(self.calibration_points_path)
        return {
            "available": bool(payload),
            "frame_path": payload.get("frame_path", ""),
            "preview_exists": self.calibration_preview_path.exists(),
        }

    def headline(self):
        t = self.tracking_summary()
        p = self.pitch_summary()
        c = self.calibration_summary()
        f = self.frames_exported()
        readiness = 0
        readiness += 30 if t["available"] else 0
        readiness += 30 if p["available"] else 0
        readiness += 20 if c["available"] else 0
        readiness += 20 if f > 0 else 0
        return {
            "readiness": readiness,
            "frames_exported": f,
            "tracking_ready": t["available"],
            "pitch_ready": p["available"],
            "calibration_ready": c["available"],
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
        self.background_dir = Path(__file__).resolve().parent / "assets" / "backgrounds"

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

        self.team_list: list[str] = []
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

        self.team_advanced_form = {}
        self.probable_lineups = {}
        self.injury_report = {}
        self.rest_profile = {}
        self.odds_movement = {}
        self.live_match_events = {}
        self.player_form = {}
        self.tactical_matchup = {}

        self.tracking_match_id = DEFAULT_TRACKING_MATCH_ID
        self.tracking_http_base_url = TRACKING_HTTP_BASE_URL
        self.tracking_ws_base_url = TRACKING_WS_BASE_URL
        self.tracking_ws_client = None
        self.tracking_last_payload = {}
        self.tracking_last_message_type = "waiting"
        self.tracking_last_status = "not connected"
        self.tracking_last_http_status = "not requested"
        self.tracking_http_refresh_inflight = False
        self.tracking_last_http_refresh_ts = 0.0
        self.tracking_status_loop_id = None
        self.tracking_bridge = TrackingArtifactBridge(SIMVISION_PROJECT_ROOT, self.tracking_match_id)

        self.build_ui()
        self.auto_load_background_defaults()
        self.apply_background_images()

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
        self.schedule_tracking_status_loop()

        self.root.protocol("WM_DELETE_WINDOW", self.quit_app)
    def refresh_match_intelligence_panels(self):
        if hasattr(self, "xg_box"):
            self.xg_box.delete("1.0", "end")
            home_adv = self.team_advanced_form.get("home", {}) if isinstance(self.team_advanced_form, dict) else {}
            away_adv = self.team_advanced_form.get("away", {}) if isinstance(self.team_advanced_form, dict) else {}
            self.xg_box.insert("end", f"Home xG: {home_adv.get('xg_for_5', home_adv.get('xg_for', '-'))}\n")
            self.xg_box.insert("end", f"Home xGA: {home_adv.get('xga_5', home_adv.get('xga', '-'))}\n")
            self.xg_box.insert("end", f"Away xG: {away_adv.get('xg_for_5', away_adv.get('xg_for', '-'))}\n")
            self.xg_box.insert("end", f"Away xGA: {away_adv.get('xga_5', away_adv.get('xga', '-'))}\n")

        if hasattr(self, "lineup_box"):
            self.lineup_box.delete("1.0", "end")
            home_line = self.probable_lineups.get("home", {}) if isinstance(self.probable_lineups, dict) else {}
            away_line = self.probable_lineups.get("away", {}) if isinstance(self.probable_lineups, dict) else {}
            self.lineup_box.insert("end", f"Home formation: {home_line.get('formation', '-')}\n")
            self.lineup_box.insert("end", f"Home strength: {home_line.get('strength_score', '-')}\n")
            self.lineup_box.insert("end", f"Away formation: {away_line.get('formation', '-')}\n")
            self.lineup_box.insert("end", f"Away strength: {away_line.get('strength_score', '-')}\n")
            self.lineup_box.insert("end", f"Home missing key: {home_line.get('key_absent_count', '-')}\n")
            self.lineup_box.insert("end", f"Away missing key: {away_line.get('key_absent_count', '-')}\n")

        if hasattr(self, "injuries_box"):
            self.injuries_box.delete("1.0", "end")
            home_inj = self.injury_report.get("home", {}) if isinstance(self.injury_report, dict) else {}
            away_inj = self.injury_report.get("away", {}) if isinstance(self.injury_report, dict) else {}
            self.injuries_box.insert("end", f"Home injury impact: {home_inj.get('impact_score', '-')}\n")
            self.injuries_box.insert("end", f"Home injured: {home_inj.get('injured_count', '-')}\n")
            self.injuries_box.insert("end", f"Home suspended: {home_inj.get('suspended_count', '-')}\n")
            self.injuries_box.insert("end", f"Away injury impact: {away_inj.get('impact_score', '-')}\n")
            self.injuries_box.insert("end", f"Away injured: {away_inj.get('injured_count', '-')}\n")
            self.injuries_box.insert("end", f"Away suspended: {away_inj.get('suspended_count', '-')}\n")

        if hasattr(self, "fatigue_box"):
            self.fatigue_box.delete("1.0", "end")
            home_rest = self.rest_profile.get("home", {}) if isinstance(self.rest_profile, dict) else {}
            away_rest = self.rest_profile.get("away", {}) if isinstance(self.rest_profile, dict) else {}
            self.fatigue_box.insert("end", f"Home days rest: {home_rest.get('days_rest', '-')}\n")
            self.fatigue_box.insert("end", f"Home fatigue: {home_rest.get('fatigue_score', '-')}\n")
            self.fatigue_box.insert("end", f"Away days rest: {away_rest.get('days_rest', '-')}\n")
            self.fatigue_box.insert("end", f"Away fatigue: {away_rest.get('fatigue_score', '-')}\n")

        if hasattr(self, "market_box"):
            self.market_box.delete("1.0", "end")
            self.market_box.insert("end", f"Home move %: {self.odds_movement.get('home_move_pct', '-')}\n")
            self.market_box.insert("end", f"Away move %: {self.odds_movement.get('away_move_pct', '-')}\n")
            self.market_box.insert("end", f"Direction: {self.odds_movement.get('direction', '-')}\n")
            self.market_box.insert("end", f"{self.prediction_engine.build_odds_caption(self.selected_fixture_odds)}\n")

        if hasattr(self, "tactical_box"):
            self.tactical_box.delete("1.0", "end")
            self.tactical_box.insert("end", f"Home tactical edge: {self.tactical_matchup.get('home_edge_score', '-')}\n")
            self.tactical_box.insert("end", f"Away tactical edge: {self.tactical_matchup.get('away_edge_score', '-')}\n")
            notes = self.tactical_matchup.get("notes", []) if isinstance(self.tactical_matchup, dict) else []
            for note in notes[:3]:
                self.tactical_box.insert("end", f"- {note}\n")

        if hasattr(self, "player_form_box"):
            self.player_form_box.delete("1.0", "end")
            home_pf = self.player_form.get("home", {}) if isinstance(self.player_form, dict) else {}
            away_pf = self.player_form.get("away", {}) if isinstance(self.player_form, dict) else {}
            self.player_form_box.insert("end", f"Home attack form: {home_pf.get('attack_form', '-')}\n")
            self.player_form_box.insert("end", f"Home defense form: {home_pf.get('defense_form', '-')}\n")
            self.player_form_box.insert("end", f"Away attack form: {away_pf.get('attack_form', '-')}\n")
            self.player_form_box.insert("end", f"Away defense form: {away_pf.get('defense_form', '-')}\n")

    # ------------------------------------------------
    # UI SHELL
    # ------------------------------------------------

    def build_ui(self):
        self.root.configure(bg=self.theme_bg)
        self._configure_ttk_theme()

        self.main = tk.Frame(self.root, bg=self.theme_bg)
        self.main.pack(fill="both", expand=True)

        self.build_top_shell()
        self.build_header_strip()
        self.build_page_background_layer()
        self.build_page_host()
        self.build_pages()
        self.apply_theme_to_widgets()
        self.show_page("live_match")

    def build_top_shell(self):
        self.top_shell = tk.Frame(self.main, bg="#060b14", height=64)
        self.top_shell.pack(fill="x")
        self.top_shell.pack_propagate(False)

        left = tk.Frame(self.top_shell, bg="#060b14")
        left.pack(side="left", fill="y", padx=12)

        mid = tk.Frame(self.top_shell, bg="#060b14")
        mid.pack(side="left", fill="both", expand=True)

        right = tk.Frame(self.top_shell, bg="#060b14")
        right.pack(side="right", fill="y", padx=12)

        self.app_title = tk.Label(
            left,
            text="JuggerNei8  Football Simulator",
            bg="#060b14",
            fg=self.text_fg,
            font=(self.font_family, 16, "bold"),
        )
        self.app_title.pack(side="left", padx=(8, 18), pady=12)

        nav_cfg = {
            "bg": "#060b14",
            "fg": self.text_fg,
            "activebackground": "#182235",
            "activeforeground": self.text_fg,
            "relief": "flat",
            "bd": 0,
            "highlightthickness": 0,
            "padx": 12,
            "pady": 6,
        }
        self.nav_live = tk.Button(mid, text="Live Match", command=lambda: self.show_page("live_match"), **nav_cfg)
        self.nav_post = tk.Button(mid, text="Post Match", command=lambda: self.show_page("post_match"), **nav_cfg)
        self.nav_club = tk.Button(mid, text="Team Overview", command=lambda: self.show_page("team_overview"), **nav_cfg)
        self.nav_squad = tk.Button(mid, text="Player Stats", command=lambda: self.show_page("player_stats"), **nav_cfg)
        self.nav_settings = tk.Button(mid, text="Settings", command=lambda: self.show_page("settings_home"), **nav_cfg)

        for btn in [self.nav_live, self.nav_post, self.nav_club, self.nav_squad, self.nav_settings]:
            btn.pack(side="left", padx=5, pady=10)

        self.global_search = tk.Entry(
            right,
            bg="#111a2b",
            fg="white",
            insertbackground="white",
            relief="flat",
            width=26,
        )
        self.global_search.pack(side="left", padx=8, pady=14)
        self.global_search.delete(0, "end")
        self.global_search.insert(0, "Search")

        self.clock_top = tk.Label(
            right,
            text="09:00",
            bg="#060b14",
            fg=self.text_fg,
            font=(self.font_family, 11, "bold"),
        )
        self.clock_top.pack(side="left", padx=10)

    def build_header_strip(self):
        self.header_strip = tk.Frame(self.main, bg="#0d1422", height=104)
        self.header_strip.pack(fill="x")
        self.header_strip.pack_propagate(False)

        left = tk.Frame(self.header_strip, bg="#0d1422")
        left.pack(side="left", fill="y", padx=16)

        center = tk.Frame(self.header_strip, bg="#0d1422")
        center.pack(side="left", fill="both", expand=True)

        right = tk.Frame(self.header_strip, bg="#0d1422")
        right.pack(side="right", fill="y", padx=16)

        self.home_logo_label = tk.Label(left, bg="#0d1422", fg=self.text_fg)
        self.home_logo_label.pack(side="left", padx=(0, 8), pady=14)

        self.home_name_label = tk.Label(
            left,
            text="HOME",
            bg="#0d1422",
            fg=self.text_fg,
            font=(self.font_family, self.header_font_size + 1, "bold"),
        )
        self.home_name_label.pack(side="left", padx=4)

        self.score_label = tk.Label(
            center,
            text="0 - 0",
            bg="#0d1422",
            fg=self.text_fg,
            font=(self.font_family, self.score_font_size + 6, "bold"),
        )
        self.score_label.pack(side="left", padx=18, pady=12)

        self.away_name_label = tk.Label(
            center,
            text="AWAY",
            bg="#0d1422",
            fg=self.text_fg,
            font=(self.font_family, self.header_font_size + 1, "bold"),
        )
        self.away_name_label.pack(side="left", padx=4)

        self.away_logo_label = tk.Label(center, bg="#0d1422", fg=self.text_fg)
        self.away_logo_label.pack(side="left", padx=(8, 18), pady=14)

        self.prediction_label = tk.Label(
            center,
            text="Prediction: waiting",
            bg="#0d1422",
            fg="#ffd166",
            font=(self.font_family, self.body_font_size + 1, "bold"),
            wraplength=760,
            justify="left",
        )
        self.prediction_label.pack(side="left", padx=10)

        self.backend_indicator = tk.Label(
            right,
            text="● Checking backend",
            bg="#0d1422",
            fg="#facc15",
            font=(self.font_family, self.body_font_size, "bold"),
        )
        self.backend_indicator.pack(anchor="e", pady=(16, 4))

        self.clock_label = tk.Label(
            right,
            text="00:00",
            bg="#0d1422",
            fg=self.text_fg,
            font=(self.font_family, self.header_font_size + 8, "bold"),
        )
        self.clock_label.pack(anchor="e")

        self.possession_label = tk.Label(
            right,
            text="Possession 50% - 50%",
            bg="#0d1422",
            fg=self.text_fg,
            font=(self.font_family, self.body_font_size),
        )
        self.possession_label.pack(anchor="e", pady=(4, 0))

    def build_page_background_layer(self):
        self.page_background_layer = tk.Label(
            self.main,
            bg=self.theme_bg,
            bd=0,
            highlightthickness=0,
            compound="center",
            anchor="center",
        )
        self.page_background_layer.place(x=0, y=168, relwidth=1, relheight=1)
        self.page_background_layer.lower()

    def build_page_host(self):
        self.page_host = tk.Frame(self.main, bg=self.theme_bg)
        self.page_host.pack(fill="both", expand=True)

    def build_pages(self):
        self.pages = {}
        for name in ["live_match", "post_match", "team_overview", "player_stats", "settings_home", "personalization"]:
            self.pages[name] = tk.Frame(self.page_host, bg=self.theme_bg)

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
        self.root.after(30, self._apply_full_page_background)
        self.root.after(50, self.apply_background_images)

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
            btn.configure(bg="#060b14")
        current = nav_map.get(self.current_page)
        if current:
            current.configure(bg="#182235")

    def make_card(self, parent, title: str):
        return tk.LabelFrame(
            parent,
            text=title,
            bg=self.card_bg,
            fg=self.text_fg,
            bd=1,
            relief="groove",
            padx=12,
            pady=12,
            font=(self.font_family, max(10, self.body_font_size), "bold"),
        )

    def make_soft_panel(self, parent, bg=None, padx=10, pady=10):
        return tk.Frame(
            parent,
            bg=bg or self.card_bg,
            bd=0,
            highlightthickness=1,
            highlightbackground="#2a3754",
            padx=padx,
            pady=pady,
        )

    def style_text_widget(self, widget):
        widget.configure(
            bg="#08101c",
            fg="white",
            insertbackground="white",
            relief="flat",
            bd=0,
            highlightthickness=1,
            highlightbackground="#22304b",
            padx=8,
            pady=8,
        )

    def _configure_ttk_theme(self):
        try:
            self.ttk_style = ttk.Style()
            self.ttk_style.theme_use("clam")
            self.ttk_style.configure(
                "TCombobox",
                fieldbackground="#101827",
                background="#101827",
                foreground="white",
                bordercolor="#334155",
                lightcolor="#334155",
                darkcolor="#334155",
                arrowcolor="white",
                padding=6,
            )
            self.ttk_style.map(
                "TCombobox",
                fieldbackground=[("readonly", "#101827")],
                foreground=[("readonly", "white")],
                selectbackground=[("readonly", "#1d4ed8")],
                selectforeground=[("readonly", "white")],
            )
        except Exception:
            pass

    def _bind_button_hover(self, button, normal_bg, hover_bg):
        def on_enter(_event):
            try:
                button.configure(bg=hover_bg)
            except Exception:
                pass

        def on_leave(_event):
            try:
                button.configure(bg=normal_bg)
            except Exception:
                pass

        button.bind("<Enter>", on_enter)
        button.bind("<Leave>", on_leave)

    def _apply_button_hover_pack(self):
        hover_pairs = []
        for btn in [self.nav_live, self.nav_post, self.nav_club, self.nav_squad, self.nav_settings]:
            hover_pairs.append((btn, "#060b14", "#182235"))

        for attr_name in [
            "btn_start_match",
            "btn_pause_match",
            "btn_reset_match",
            "btn_refresh_data",
            "btn_open_settings",
            "btn_tracking_subscribe",
            "btn_tracking_unsubscribe",
            "btn_tracking_refresh",
            "btn_personalization_open",
            "btn_refresh_high",
            "btn_refresh_balanced",
            "btn_refresh_saver",
            "btn_toggle_mute",
            "btn_personalization_ok",
            "btn_personalization_back",
        ]:
            btn = getattr(self, attr_name, None)
            if btn is not None:
                hover_pairs.append((btn, self.accent, "#7c3aed"))

        for button, normal_bg, hover_bg in hover_pairs:
            self._bind_button_hover(button, normal_bg, hover_bg)

    def _page_background_choice(self, page_name: str):
        if page_name in {"live_match", "post_match"}:
            return self.stadium_background_path or self.general_background_path
        if page_name in {"team_overview", "player_stats"}:
            return self.main_background_path or self.general_background_path
        return self.general_background_path or self.main_background_path

    # ------------------------------------------------
    # BACKGROUND HELPERS
    # ------------------------------------------------

    def auto_load_background_defaults(self):
        defaults = {
            "main": self.background_dir / "main_bg.png",
            "general": self.background_dir / "general_bg.png",
            "pitch": self.background_dir / "pitch_bg.png",
            "stadium": self.background_dir / "stadium_bg.png",
        }
        if not self.main_background_path and defaults["main"].exists():
            self.main_background_path = str(defaults["main"])
        if not self.general_background_path and defaults["general"].exists():
            self.general_background_path = str(defaults["general"])
        if not self.pitch_background_path and defaults["pitch"].exists():
            self.pitch_background_path = str(defaults["pitch"])
        if not self.stadium_background_path and defaults["stadium"].exists():
            self.stadium_background_path = str(defaults["stadium"])

    def _safe_photoimage(self, path: str, target_size=None):
        if not path:
            return None
        try:
            if Image is not None and ImageTk is not None:
                image = Image.open(path)
                image.load()
                if target_size:
                    image = image.resize(target_size, Image.LANCZOS)
                return ImageTk.PhotoImage(image)
            return tk.PhotoImage(file=path)
        except Exception as e:
            logger.warning("Could not load image %s: %s", path, e)
            return None

    def _fit_image_to_size(self, path: str, width: int, height: int):
        if not path:
            return None
        try:
            if Image is None or ImageTk is None:
                return self._safe_photoimage(path)

            image = Image.open(path)
            image.load()
            src_w, src_h = image.size
            if src_w <= 0 or src_h <= 0 or width <= 0 or height <= 0:
                return ImageTk.PhotoImage(image)

            scale = max(width / src_w, height / src_h)
            new_w = max(1, int(src_w * scale))
            new_h = max(1, int(src_h * scale))
            image = image.resize((new_w, new_h), Image.LANCZOS)

            left = max(0, (new_w - width) // 2)
            top = max(0, (new_h - height) // 2)
            image = image.crop((left, top, left + width, top + height))
            return ImageTk.PhotoImage(image)
        except Exception as e:
            logger.warning("Could not fit image %s: %s", path, e)
            return None

    def _apply_banner_image(self, label_widget, preferred_path, fallback_path, fallback_text):
        if not label_widget:
            return

        label_widget.update_idletasks()
        width = max(900, label_widget.winfo_width() or 0)
        height = max(180, label_widget.winfo_height() or 0)

        image = self._fit_image_to_size(preferred_path, width, height)
        if image is None and fallback_path:
            image = self._fit_image_to_size(fallback_path, width, height)

        if image is not None:
            label_widget.config(image=image, text="")
            label_widget.image = image
        else:
            label_widget.config(image="", text=fallback_text, fg=self.text_fg)

    def _apply_full_page_background(self):
        if not hasattr(self, "page_background_layer"):
            return

        self.page_background_layer.update_idletasks()
        width = max(1200, self.page_background_layer.winfo_width() or 0)
        height = max(700, self.page_background_layer.winfo_height() or 0)

        path = self._page_background_choice(self.current_page)
        image = self._fit_image_to_size(path, width, height) if path else None

        if image is not None:
            self.page_background_layer.configure(image=image, text="")
            self.page_background_layer.image = image
        else:
            self.page_background_layer.configure(image="", text="", bg=self.theme_bg)

    def apply_background_images(self):
        if hasattr(self, "live_bg_banner"):
            self._apply_banner_image(
                self.live_bg_banner,
                self.stadium_background_path,
                self.general_background_path,
                "Live Match Background",
            )
        if hasattr(self, "post_bg_banner"):
            self._apply_banner_image(
                self.post_bg_banner,
                self.stadium_background_path,
                self.general_background_path,
                "Post Match Background",
            )
        if hasattr(self, "team_bg_banner"):
            self._apply_banner_image(
                self.team_bg_banner,
                self.main_background_path,
                self.general_background_path,
                "Team Overview Background",
            )
        if hasattr(self, "player_bg_banner"):
            self._apply_banner_image(
                self.player_bg_banner,
                self.main_background_path,
                self.general_background_path,
                "Player Stats Background",
            )
        if hasattr(self, "settings_bg_banner"):
            self._apply_banner_image(
                self.settings_bg_banner,
                self.general_background_path,
                self.main_background_path,
                "Settings Background",
            )
        self._apply_full_page_background()

    def refresh_background_labels(self):
        if hasattr(self, "main_bg_label"):
            self.main_bg_label.config(text=f"Main image: {self.main_background_path or 'not set'}")
        if hasattr(self, "general_bg_label"):
            self.general_bg_label.config(text=f"General image: {self.general_background_path or 'not set'}")
        if hasattr(self, "pitch_bg_label"):
            self.pitch_bg_label.config(text=f"Pitch image: {self.pitch_background_path or 'not set'}")
        if hasattr(self, "stadium_bg_label"):
            self.stadium_bg_label.config(text=f"Stadium image: {self.stadium_background_path or 'not set'}")

    # ------------------------------------------------
    # PAGE BUILDERS
    # ------------------------------------------------

    def build_live_match_page(self):
        page = self.pages["live_match"]

        top = tk.Frame(page, bg=self.theme_bg)
        top.pack(fill="x", padx=12, pady=(12, 8))

        self.live_detail_label = tk.Label(
            top,
            text="Live Match Dashboard",
            bg=self.theme_bg,
            fg=self.text_fg,
            font=(self.font_family, 20, "bold"),
        )
        self.live_detail_label.pack(side="left")

        self.live_page_status = tk.Label(
            top,
            text="Broadcast control room",
            bg=self.theme_bg,
            fg=self.accent,
            font=(self.font_family, self.body_font_size + 1, "bold"),
        )
        self.live_page_status.pack(side="right")

        self.live_bg_banner = tk.Label(
            page,
            text="",
            bg=self.card_bg,
            fg=self.text_fg,
            height=11,
            anchor="center",
            compound="center",
        )
        self.live_bg_banner.pack(fill="x", padx=12, pady=(0, 12))

        body = tk.Frame(page, bg=self.theme_bg)
        body.pack(fill="both", expand=True, padx=12, pady=(0, 12))

        self.live_left = tk.Frame(body, bg=self.theme_bg, width=320)
        self.live_left.pack(side="left", fill="y", padx=(0, 8))
        self.live_left.pack_propagate(False)

        self.live_center = tk.Frame(body, bg=self.theme_bg)
        self.live_center.pack(side="left", fill="both", expand=True, padx=8)

        self.live_right = tk.Frame(body, bg=self.theme_bg, width=420)
        self.live_right.pack(side="right", fill="y", padx=(8, 0))
        self.live_right.pack_propagate(False)

        self.build_live_left_column()
        self.build_live_center_column()
        self.build_live_right_column()

    def build_live_left_column(self):
        card = self.make_card(self.live_left, "Match Controls")
        card.pack(fill="x", pady=(0, 10))

        tk.Label(card, text="League", bg=self.card_bg, fg=self.text_fg).pack(anchor="w")
        self.league_box = ttk.Combobox(card, values=list(LEAGUE_OPTIONS.keys()), state="readonly")
        self.league_box.pack(fill="x", pady=(2, 8))
        self.league_box.set(self._league_name_from_code(self.current_competition))
        self.league_box.bind("<<ComboboxSelected>>", self.on_league_changed)

        home_row = tk.Frame(card, bg=self.card_bg)
        home_row.pack(fill="x", pady=4)
        tk.Label(home_row, text="Home", bg=self.card_bg, fg=self.text_fg, width=8, anchor="w").pack(side="left")
        self.home_box = ttk.Combobox(home_row, values=self.team_list, state="normal")
        self.home_box.pack(side="left", fill="x", expand=True)
        self.home_box.bind("<<ComboboxSelected>>", self.on_team_selection_changed)

        away_row = tk.Frame(card, bg=self.card_bg)
        away_row.pack(fill="x", pady=4)
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

        btn_cfg = {
            "bg": self.accent,
            "fg": "white",
            "relief": "flat",
            "activebackground": self.accent,
            "activeforeground": "white",
            "padx": 10,
            "pady": 8,
        }
        self.btn_start_match = tk.Button(card, text="Start Match", command=self.start_match, **btn_cfg)
        self.btn_start_match.pack(fill="x", pady=4)

        self.btn_pause_match = tk.Button(card, text="Pause Match", command=self.pause_match, **btn_cfg)
        self.btn_pause_match.pack(fill="x", pady=4)

        self.btn_reset_match = tk.Button(card, text="Reset Match", command=self.reset_match, **btn_cfg)
        self.btn_reset_match.pack(fill="x", pady=4)

        self.btn_refresh_data = tk.Button(card, text="Refresh Data", command=self.load_initial_data, **btn_cfg)
        self.btn_refresh_data.pack(fill="x", pady=4)

        self.btn_open_settings = tk.Button(card, text="Settings", command=lambda: self.show_page("settings_home"), **btn_cfg)
        self.btn_open_settings.pack(fill="x", pady=4)

        info_card = self.make_card(self.live_left, "Live Notes")
        info_card.pack(fill="both", expand=True)

        self.tactic_label = tk.Label(
            info_card,
            text="Live tactics: waiting",
            bg=self.card_bg,
            fg="#cbd5e1",
            justify="left",
            wraplength=260,
            anchor="nw",
        )
        self.tactic_label.pack(fill="x", pady=4)

        self.form_label = tk.Label(
            info_card,
            text="Team form: waiting",
            bg=self.card_bg,
            fg="#93c5fd",
            justify="left",
            wraplength=260,
            anchor="nw",
        )
        self.form_label.pack(fill="x", pady=4)

        self.commentary_box = tk.Text(info_card, height=18, wrap="word")
        self.style_text_widget(self.commentary_box)
        self.commentary_box.pack(fill="both", expand=True, pady=(8, 0))

    def build_live_center_column(self):
        score_card = self.make_card(self.live_center, "Live Match")
        score_card.pack(fill="x", pady=(0, 10))

        self.live_match_detail = tk.Label(
            score_card,
            text="Home vs Away | 00:00",
            bg=self.card_bg,
            fg=self.text_fg,
            font=(self.font_family, 14, "bold"),
        )
        self.live_match_detail.pack(anchor="w")

        canvas_wrap = self.make_soft_panel(self.live_center, bg=self.card_bg, padx=8, pady=8)
        canvas_wrap.pack(fill="both", expand=True, pady=(0, 10))

        self.canvas = tk.Canvas(
            canvas_wrap,
            bg=self.pitch_bg,
            highlightthickness=0,
            cursor="crosshair",
            height=440,
        )
        self.canvas.pack(fill="both", expand=True)

        bottom_row = tk.Frame(self.live_center, bg=self.theme_bg)
        bottom_row.pack(fill="x")

        stats_card = self.make_card(bottom_row, "Match Stats")
        stats_card.pack(side="left", fill="both", expand=True, padx=(0, 5))
        self.stats_box = tk.Text(stats_card, height=10, wrap="word")
        self.style_text_widget(self.stats_box)
        self.stats_box.pack(fill="both", expand=True)

        timeline_card = self.make_card(bottom_row, "Match Events")
        timeline_card.pack(side="left", fill="both", expand=True, padx=(5, 0))
        self.timeline_box = tk.Text(timeline_card, height=10, wrap="word")
        self.style_text_widget(self.timeline_box)
        self.timeline_box.pack(fill="both", expand=True)


    def build_live_right_column(self):
        compare = self.make_card(self.live_right, "Comparison")
        compare.pack(fill="x", pady=(0, 8))

        self.compare_title = tk.Label(compare, text="Home vs Away", bg=self.card_bg, fg=self.text_fg, font=(self.font_family, 11, "bold"))
        self.compare_title.pack(anchor="w")

        self.compare_record_label = tk.Label(compare, text="Wins recent: -", bg=self.card_bg, fg=self.text_fg)
        self.compare_record_label.pack(anchor="w", pady=(6, 2))

        self.wins_bar = tk.Canvas(compare, height=20, bg="#08101c", highlightthickness=0)
        self.wins_bar.pack(fill="x", pady=(0, 6))

        self.compare_goals_label = tk.Label(compare, text="Goals recent: -", bg=self.card_bg, fg=self.text_fg)
        self.compare_goals_label.pack(anchor="w", pady=(2, 2))

        self.goals_bar = tk.Canvas(compare, height=20, bg="#08101c", highlightthickness=0)
        self.goals_bar.pack(fill="x")

        odds_card = self.make_card(self.live_right, "Selected Match Odds")
        odds_card.pack(fill="x", pady=(0, 8))
        odds_row = tk.Frame(odds_card, bg=self.card_bg)
        odds_row.pack(fill="x")
        self.odds_card_home_value = self._make_odds_box(odds_row, "HOME")
        self.odds_card_draw_value = self._make_odds_box(odds_row, "DRAW")
        self.odds_card_away_value = self._make_odds_box(odds_row, "AWAY")

        self.prediction_summary_box = self._make_text_panel(self.live_right, "Prediction Summary", 4)
        self.verdict_box = self._make_text_panel(self.live_right, "Likely Winner", 3)
        self.scoreline_box = self._make_text_panel(self.live_right, "Scoreline Tendency", 3)
        self.xg_box = self._make_text_panel(self.live_right, "xG / xGA", 4)
        self.market_box = self._make_text_panel(self.live_right, "Ongoing Market", 4)

        notebook_wrap = self.make_card(self.live_right, "Match Center")
        notebook_wrap.pack(fill="both", expand=True, pady=(6, 0))

        self.right_notebook = ttk.Notebook(notebook_wrap)
        self.right_notebook.pack(fill="both", expand=True)

        self.match_center_tab = tk.Frame(self.right_notebook, bg=self.card_bg)
        self.intelligence_tab = tk.Frame(self.right_notebook, bg=self.card_bg)
        self.tracking_tab = tk.Frame(self.right_notebook, bg=self.card_bg)

        self.right_notebook.add(self.match_center_tab, text="Match Center")
        self.right_notebook.add(self.intelligence_tab, text="Intelligence")
        self.right_notebook.add(self.tracking_tab, text="Tracking")

        self.selected_match_details_box = self._make_text_panel(self.match_center_tab, "Selected Incoming Match", 7)
        self.bookmarked_games_box = self._make_text_panel(self.match_center_tab, "Scheduled Bookmarked Games", 6)
        self.live_games_box = self._make_text_panel(self.match_center_tab, "Live Ongoing Games", 6)
        self.scheduled_games_box = self._make_text_panel(self.match_center_tab, "Scheduled Games", 6)
        self.live_market_box = self._make_text_panel(self.match_center_tab, "Live Market Odds", 5)
        self.scheduled_market_box = self._make_text_panel(self.match_center_tab, "Scheduled Market Odds", 5)
        self.match_history_context_box = self._make_text_panel(self.match_center_tab, "History Context", 8)
        self.match_data_box = self._make_text_panel(self.match_center_tab, "Match Data", 4)
        self.table_box = self._make_text_panel(self.match_center_tab, "Live Table", 5)
        self.stats_summary_box = self._make_text_panel(self.match_center_tab, "Game Stats Summary", 4)

        self.lineup_box = self._make_text_panel(self.intelligence_tab, "Probable Lineups", 5)
        self.injuries_box = self._make_text_panel(self.intelligence_tab, "Injuries / Suspensions", 5)
        self.fatigue_box = self._make_text_panel(self.intelligence_tab, "Rest / Fatigue", 4)
        self.tactical_box = self._make_text_panel(self.intelligence_tab, "Tactical Matchup", 5)
        self.player_form_box = self._make_text_panel(self.intelligence_tab, "Player Form", 4)

        self.build_tracking_stream_card(parent_override=self.tracking_tab)
        self.build_tracking_analysis_card(parent_override=self.tracking_tab)
        self.build_live_metrics_api_card(parent_override=self.tracking_tab)
        self.build_live_tactical_api_card(parent_override=self.tracking_tab)

    def build_tracking_stream_card(self, parent_override=None):
        parent = parent_override or self.live_right
        card = self.make_card(parent, "Tracking Stream")
        card.pack(fill="x", pady=(4, 8))

        self.tracking_match_label = tk.Label(
            card,
            text=f"Match ID: {self.tracking_match_id}",
            bg=self.card_bg,
            fg=self.text_fg,
            justify="left",
            anchor="w",
        )
        self.tracking_match_label.pack(fill="x", pady=2)

        self.tracking_ws_label = tk.Label(
            card,
            text=f"WS: {self.tracking_ws_base_url}",
            bg=self.card_bg,
            fg=self.accent2,
            justify="left",
            wraplength=340,
            anchor="w",
        )
        self.tracking_ws_label.pack(fill="x", pady=2)

        self.tracking_http_label = tk.Label(
            card,
            text=f"HTTP: {self.tracking_http_base_url}",
            bg=self.card_bg,
            fg=self.accent2,
            justify="left",
            wraplength=340,
            anchor="w",
        )
        self.tracking_http_label.pack(fill="x", pady=2)

        self.tracking_socket_state_label = tk.Label(
            card,
            text="Socket: not connected",
            bg=self.card_bg,
            fg="#facc15",
            justify="left",
            anchor="w",
        )
        self.tracking_socket_state_label.pack(fill="x", pady=(8, 2))

        self.tracking_event_label = tk.Label(
            card,
            text="Last event: waiting",
            bg=self.card_bg,
            fg=self.text_fg,
            justify="left",
            wraplength=340,
            anchor="w",
        )
        self.tracking_event_label.pack(fill="x", pady=2)

        self.tracking_video_status_label = tk.Label(
            card,
            text="Video status: not requested",
            bg=self.card_bg,
            fg=self.text_fg,
            justify="left",
            wraplength=340,
            anchor="w",
        )
        self.tracking_video_status_label.pack(fill="x", pady=(2, 8))

        btn_row = tk.Frame(card, bg=self.card_bg)
        btn_row.pack(fill="x")

        btn_cfg = {
            "bg": self.accent,
            "fg": "white",
            "relief": "flat",
            "activebackground": self.accent,
            "activeforeground": "white",
            "padx": 10,
            "pady": 8,
        }
        self.btn_tracking_subscribe = tk.Button(btn_row, text="Subscribe", command=self.start_tracking_subscription, **btn_cfg)
        self.btn_tracking_subscribe.pack(side="left", expand=True, fill="x", padx=(0, 4))

        self.btn_tracking_unsubscribe = tk.Button(btn_row, text="Unsubscribe", command=self.stop_tracking_subscription, **btn_cfg)
        self.btn_tracking_unsubscribe.pack(side="left", expand=True, fill="x", padx=4)

        self.btn_tracking_refresh = tk.Button(
            btn_row,
            text="Refresh Status",
            command=lambda: self.refresh_tracking_http_status(force=True),
            **btn_cfg,
        )
        self.btn_tracking_refresh.pack(side="left", expand=True, fill="x", padx=(4, 0))

    def build_live_analysis_api_card(self, parent_override=None):
        parent = parent_override or self.live_right
        card = self.make_card(parent, "Live Analysis API")
        card.pack(fill="both", expand=True, pady=(0, 8))

        self.live_analysis_status_label = tk.Label(
            card,
            text="Live analysis API waiting...",
            bg=self.card_bg,
            fg="#fbbf24",
            justify="left",
            anchor="w",
        )
        self.live_analysis_status_label.pack(fill="x", pady=(0, 8))

        self.live_analysis_box = tk.Text(card, height=10, wrap="word")
        self.style_text_widget(self.live_analysis_box)
        self.live_analysis_box.pack(fill="both", expand=True)

        bottom = tk.Frame(card, bg=self.card_bg)
        bottom.pack(fill="x", pady=(8, 0))

        btn_cfg = {
            "bg": self.accent,
            "fg": "white",
            "relief": "flat",
            "activebackground": self.accent,
            "activeforeground": "white",
            "padx": 10,
            "pady": 8,
        }

        self.btn_live_analysis_refresh = tk.Button(
            bottom, text="Refresh Analysis", command=self.refresh_live_analysis_panel, **btn_cfg
        )
        self.btn_live_analysis_refresh.pack(side="left", padx=(0, 6))

        self.btn_live_analysis_start = tk.Button(
            bottom, text="Start Worker", command=self.start_live_analysis_worker, **btn_cfg
        )
        self.btn_live_analysis_start.pack(side="left", padx=6)

    def build_live_metrics_api_card(self, parent_override=None):
        parent = parent_override or self.live_right
        card = self.make_card(parent, "Live Player Metrics API")
        card.pack(fill="both", expand=True, pady=(0, 8))

        self.live_metrics_status_label = tk.Label(
            card,
            text="Metrics API waiting...",
            bg=self.card_bg,
            fg="#fbbf24",
            justify="left",
            anchor="w",
        )
        self.live_metrics_status_label.pack(fill="x", pady=(0, 8))

        self.live_metrics_box = tk.Text(card, height=10, wrap="word")
        self.style_text_widget(self.live_metrics_box)
        self.live_metrics_box.pack(fill="both", expand=True)

        bottom = tk.Frame(card, bg=self.card_bg)
        bottom.pack(fill="x", pady=(8, 0))

        btn_cfg = {
            "bg": self.accent,
            "fg": "white",
            "relief": "flat",
            "activebackground": self.accent,
            "activeforeground": "white",
            "padx": 10,
            "pady": 8,
        }

        self.btn_live_metrics_refresh = tk.Button(
            bottom, text="Refresh Metrics", command=self.refresh_live_metrics_panel, **btn_cfg
        )
        self.btn_live_metrics_refresh.pack(side="left", padx=(0, 6))

    def build_tracking_analysis_card(self, parent_override=None):
        parent = parent_override or self.live_right
        card = self.make_card(parent, "Tracking Analysis")
        card.pack(fill="both", expand=True, pady=(0, 0))

        self.tracking_analysis_status = tk.Label(
            card,
            text="Tracking analysis waiting...",
            bg=self.card_bg,
            fg="#fbbf24",
            justify="left",
            anchor="w",
        )
        self.tracking_analysis_status.pack(fill="x", pady=(0, 8))

        self.tracking_analysis_box = tk.Text(card, height=14, wrap="word")
        self.style_text_widget(self.tracking_analysis_box)
        self.tracking_analysis_box.pack(fill="both", expand=True)

        bottom = tk.Frame(card, bg=self.card_bg)
        bottom.pack(fill="x", pady=(8, 0))

        btn_cfg = {
            "bg": self.accent,
            "fg": "white",
            "relief": "flat",
            "activebackground": self.accent,
            "activeforeground": "white",
            "padx": 10,
            "pady": 8,
        }
        self.btn_tracking_analysis_refresh = tk.Button(
            bottom,
            text="Refresh Analysis",
            command=self.refresh_tracking_analysis_panel,
            **btn_cfg,
        )
        self.btn_tracking_analysis_refresh.pack(side="left", padx=(0, 6))

        self.btn_tracking_workbench = tk.Button(
            bottom,
            text="Open Workbench",
            command=self.open_calibration_workbench,
            **btn_cfg,
        )
        self.btn_tracking_workbench.pack(side="left", padx=6)

    def refresh_tracking_analysis_panel(self):
        self.tracking_bridge = TrackingArtifactBridge(SIMVISION_PROJECT_ROOT, self.tracking_match_id)
        headline = self.tracking_bridge.headline()
        tracking = self.tracking_bridge.tracking_summary()
        pitch = self.tracking_bridge.pitch_summary()
        calibration = self.tracking_bridge.calibration_summary()

        if hasattr(self, "tracking_analysis_status"):
            self.tracking_analysis_status.config(
                text=(
                    f"Readiness {headline['readiness']}/100 | "
                    f"Tracking={headline['tracking_ready']} | "
                    f"PitchMap={headline['pitch_ready']} | "
                    f"Calibration={headline['calibration_ready']}"
                )
            )

        if hasattr(self, "tracking_analysis_box"):
            self.tracking_analysis_box.delete("1.0", "end")
            lines = [
                f"Match ID: {self.tracking_match_id}",
                f"Readiness Score: {headline['readiness']}/100",
                "",
                f"Tracking Ready: {headline['tracking_ready']}",
                f"Pitch Map Ready: {headline['pitch_ready']}",
                f"Calibration Ready: {headline['calibration_ready']}",
                f"Frames Exported: {headline['frames_exported']}",
                "",
                f"Tracking Processor: {tracking['processor']}",
                f"Tracking Status: {tracking['status']}",
                f"Frames Processed: {tracking['frames_processed']}",
                f"Player Tracks: {tracking['player_tracks']}",
                f"Ball Tracks: {tracking['ball_tracks']}",
                f"Home Team Tracks: {tracking['home_team_tracks']}",
                f"Away Team Tracks: {tracking['away_team_tracks']}",
                f"Official Tracks: {tracking['official_tracks']}",
                f"Goalkeeper Candidates: {tracking['goalkeeper_candidates']}",
                "",
                f"Pitch Map Method: {pitch['method']}",
                f"Calibration Used: {pitch['calibration_used']}",
                f"Mapped Points: {pitch['mapped_points']}",
                f"Orientation Confidence: {pitch['orientation_confidence']}",
                "",
                f"Calibration Preview Exists: {calibration['preview_exists']}",
                f"Calibration Frame: {calibration['frame_path']}",
                f"Tracking Output: {self.tracking_bridge.tracking_output_path}",
                f"Pitch Map: {self.tracking_bridge.pitch_map_path}",
            ]
            for line in lines:
                self.tracking_analysis_box.insert("end", line + "\n")

    def open_calibration_workbench(self):
        workbench_path = SIMVISION_PROJECT_ROOT / "tools" / "calibration_workbench.py"
        if not workbench_path.exists():
            messagebox.showerror("Missing Workbench", f"Could not find:\n{workbench_path}")
            return
        try:
            import subprocess
            subprocess.Popen(
                [
                    "python",
                    str(workbench_path),
                    "--project-root", str(SIMVISION_PROJECT_ROOT),
                    "--match-id", self.tracking_match_id,
                    "--api-base-url", self.tracking_http_base_url,
                ],
                cwd=str(SIMVISION_PROJECT_ROOT),
            )
        except Exception as exc:
            messagebox.showerror("Launch Error", str(exc))

    def build_live_tactical_api_card(self, parent_override=None):
        parent = parent_override or self.live_right
        card = self.make_card(parent, "Live Tactical API")
        card.pack(fill="both", expand=True, pady=(0, 8))

        self.live_tactical_status_label = tk.Label(
            card,
            text="Tactical API waiting...",
            bg=self.card_bg,
            fg="#fbbf24",
            justify="left",
            anchor="w",
        )
        self.live_tactical_status_label.pack(fill="x", pady=(0, 8))

        self.live_tactical_box = tk.Text(card, height=10, wrap="word")
        self.style_text_widget(self.live_tactical_box)
        self.live_tactical_box.pack(fill="both", expand=True)

        bottom = tk.Frame(card, bg=self.card_bg)
        bottom.pack(fill="x", pady=(8, 0))

        btn_cfg = {
            "bg": self.accent,
            "fg": "white",
            "relief": "flat",
            "activebackground": self.accent,
            "activeforeground": "white",
            "padx": 10,
            "pady": 8,
        }

        self.btn_live_tactical_refresh = tk.Button(
            bottom, text="Refresh Tactical", command=self.refresh_live_tactical_panel, **btn_cfg
        )
        self.btn_live_tactical_refresh.pack(side="left", padx=(0, 6))

    def refresh_live_analysis_panel(self):
        self.live_analysis_status_label.config(text="Refreshing live analysis...")
        self.live_analysis_box.delete("1.0", "end")
        self.live_analysis_box.insert("end", "Live analysis refresh requested.\n")

    def start_live_analysis_worker(self):
        self.live_analysis_status_label.config(text="Live analysis worker start requested")
        self.live_analysis_box.insert("end", "Start worker clicked.\n")

    def refresh_live_metrics_panel(self):
        self.live_metrics_status_label.config(text="Refreshing metrics...")
        self.live_metrics_box.delete("1.0", "end")
        self.live_metrics_box.insert("end", "Metrics refresh requested.\n")

    def refresh_live_tactical_panel(self):
        self.live_tactical_status_label.config(text="Refreshing tactical feed...")
        self.live_tactical_box.delete("1.0", "end")
        self.live_tactical_box.insert("end", "Tactical refresh requested.\n")

    def build_post_match_page(self):
        page = self.pages["post_match"]

        title = tk.Label(page, text="Post Match Report", bg=self.theme_bg, fg=self.text_fg, font=(self.font_family, 18, "bold"))
        title.pack(anchor="w", padx=10, pady=(10, 6))

        self.post_bg_banner = tk.Label(
            page,
            text="Post Match Background",
            bg=self.card_bg,
            fg=self.text_fg,
            height=10,
            anchor="center",
            compound="center",
        )
        self.post_bg_banner.pack(fill="x", padx=10, pady=(0, 12))

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

    def build_team_overview_page(self):
        page = self.pages["team_overview"]

        header = tk.Label(page, text="Team Overview", bg=self.theme_bg, fg=self.text_fg, font=(self.font_family, 18, "bold"))
        header.pack(anchor="w", padx=10, pady=(10, 6))

        self.team_bg_banner = tk.Label(
            page,
            text="Team Overview Background",
            bg=self.card_bg,
            fg=self.text_fg,
            height=10,
            anchor="center",
            compound="center",
        )
        self.team_bg_banner.pack(fill="x", padx=10, pady=(0, 12))

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

    def build_player_stats_page(self):
        page = self.pages["player_stats"]

        header = tk.Label(page, text="Player / Staff Stats", bg=self.theme_bg, fg=self.text_fg, font=(self.font_family, 18, "bold"))
        header.pack(anchor="w", padx=10, pady=(10, 6))

        self.player_bg_banner = tk.Label(
            page,
            text="Player Stats Background",
            bg=self.card_bg,
            fg=self.text_fg,
            height=10,
            anchor="center",
            compound="center",
        )
        self.player_bg_banner.pack(fill="x", padx=10, pady=(0, 12))

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

    def build_settings_home_page(self):
        page = self.pages["settings_home"]

        title = tk.Label(page, text="Settings", bg=self.theme_bg, fg=self.text_fg, font=(self.font_family, 18, "bold"))
        title.pack(anchor="w", padx=10, pady=(10, 6))

        self.settings_bg_banner = tk.Label(
            page,
            text="Settings Background",
            bg=self.card_bg,
            fg=self.text_fg,
            height=10,
            anchor="center",
            compound="center",
        )
        self.settings_bg_banner.pack(fill="x", padx=10, pady=(0, 12))

        card = self.make_card(page, "Match View / System")
        card.pack(fill="x", padx=10, pady=(0, 8))

        tk.Label(
            card,
            text="Choose camera style, graphics quality, match sounds, and personalization.",
            bg=self.card_bg,
            fg=self.text_fg,
            justify="left",
        ).pack(anchor="w", pady=(0, 10))

        btn_cfg = {
            "bg": self.accent,
            "fg": "white",
            "relief": "flat",
            "activebackground": self.accent,
            "activeforeground": "white",
            "padx": 10,
            "pady": 8,
        }

        self.btn_personalization_open = tk.Button(card, text="Personalization", command=lambda: self.show_page("personalization"), **btn_cfg)
        self.btn_personalization_open.pack(fill="x", pady=4)

        self.btn_refresh_high = tk.Button(card, text="High Refresh", command=lambda: self.set_refresh_quality("high"), **btn_cfg)
        self.btn_refresh_high.pack(fill="x", pady=4)

        self.btn_refresh_balanced = tk.Button(card, text="Balanced Refresh", command=lambda: self.set_refresh_quality("balanced"), **btn_cfg)
        self.btn_refresh_balanced.pack(fill="x", pady=4)

        self.btn_refresh_saver = tk.Button(card, text="Saver Refresh", command=lambda: self.set_refresh_quality("saver"), **btn_cfg)
        self.btn_refresh_saver.pack(fill="x", pady=4)

        self.btn_toggle_mute = tk.Button(card, text="Mute / Unmute", command=self.toggle_mute, **btn_cfg)
        self.btn_toggle_mute.pack(fill="x", pady=4)

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
        self.pitch_color_box = ttk.Combobox(
            theme_card,
            values=["#2e7d32", "#1f8f46", "#3f9c35", "#245b2a", "#4caf50"],
            state="readonly",
        )
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

        self.btn_personalization_ok = tk.Button(side_card, text="OK", command=self.apply_personalization_settings, bg=self.accent, fg="white", relief="flat")
        self.btn_personalization_ok.pack(fill="x", pady=4)

        self.btn_personalization_back = tk.Button(side_card, text="Back", command=lambda: self.show_page("settings_home"), bg=self.accent2, fg="white", relief="flat")
        self.btn_personalization_back.pack(fill="x", pady=4)

        self.refresh_background_labels()

    # ------------------------------------------------
    # HELPERS / CALLBACKS
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
        box = tk.Text(wrap, height=height, wrap="word")
        self.style_text_widget(box)
        box.pack(fill="x")
        return box

    def add_commentary(self, text):
        if hasattr(self, "commentary_box"):
            self.commentary_box.insert("end", text + "\n")
            self.commentary_box.see("end")

    def update_stats(self, stats):
        if not hasattr(self, "stats_box"):
            return

        self.stats_box.delete("1.0", "end")
        for k, v in stats.items():
            self.stats_box.insert("end", f"{k}: {v}\n")

        if hasattr(self, "post_stats_box"):
            self.post_stats_box.delete("1.0", "end")
            for k, v in stats.items():
                self.post_stats_box.insert("end", f"{k}: {v}\n")

        if hasattr(self, "stats_summary_box"):
            self.stats_summary_box.delete("1.0", "end")
            self.stats_summary_box.insert("end", "Live game stats\n")
            for k, v in stats.items():
                self.stats_summary_box.insert("end", f"{k}: {v}\n")
            self.stats_summary_box.insert("end", f"Odds: {self.prediction_engine.build_odds_caption(self.selected_fixture_odds)}\n")

    def add_timeline_event(self, minute, kind, text):
        self.timeline_engine.add_event(minute, kind, text)
        lines = self.timeline_engine.as_lines(limit=24)

        if hasattr(self, "timeline_box"):
            self.timeline_box.delete("1.0", "end")
            for line in lines:
                self.timeline_box.insert("end", line + "\n")

        if hasattr(self, "post_events_box"):
            self.post_events_box.delete("1.0", "end")
            for line in lines:
                self.post_events_box.insert("end", line + "\n")

    # ------------------------------------------------
    # TRACKING STREAM
    # ------------------------------------------------

    def schedule_tracking_status_loop(self):
        if self.tracking_status_loop_id is not None:
            return
        self.tracking_status_loop_id = self.root.after(TRACKING_STATUS_POLL_MS, self._tracking_status_loop)

    def _tracking_status_loop(self):
        self.tracking_status_loop_id = None
        self.refresh_tracking_http_status(silent=True)
        self.refresh_tracking_analysis_panel()
        self.schedule_tracking_status_loop()

    def start_tracking_subscription(self):
        if self.tracking_ws_client and self.tracking_ws_client.is_connected:
            self.add_commentary("Tracking stream already connected.")
            return

        self.stop_tracking_subscription(silent=True)

        self.tracking_ws_client = EmbeddedTrackingWebSocketClient(
            self.tracking_ws_base_url,
            self.tracking_match_id,
            self._handle_tracking_message,
            self._handle_tracking_status,
        )
        self.tracking_ws_client.start()
        self.add_commentary(f"Tracking subscription requested for {self.tracking_match_id}.")

    def stop_tracking_subscription(self, silent=False):
        if self.tracking_ws_client:
            try:
                self.tracking_ws_client.stop()
            except Exception as exc:
                logger.warning("Tracking socket stop warning: %s", exc)
            self.tracking_ws_client = None

        self.tracking_last_status = "not connected"
        self.root.after(0, self._render_tracking_state)
        if not silent:
            self.add_commentary("Tracking subscription stopped.")

    def _handle_tracking_status(self, status):
        self.tracking_last_status = status
        self.root.after(0, self._render_tracking_state)

        lowered = status.lower()
        if "connected" in lowered and "connecting" not in lowered:
            self.root.after(250, lambda: self.refresh_tracking_http_status(silent=True, force=True))
            self.root.after(350, self.refresh_tracking_analysis_panel)

    def _handle_tracking_message(self, payload):
        self.tracking_last_payload = payload or {}
        self.tracking_last_message_type = self.tracking_last_payload.get("type", "unknown")
        self.root.after(0, self._render_tracking_state)

        if self.tracking_last_message_type != "heartbeat":
            self.root.after(0, lambda: self.add_commentary(f"Tracking update: {self.tracking_last_message_type}"))

        if self.tracking_last_message_type in {
            "video_tracking_started",
            "video_tracking_completed",
            "pitch_mapping_started",
            "pitch_mapping_completed",
            "tracked",
        }:
            self.root.after(0, lambda: self.refresh_tracking_http_status(silent=True, force=True))
            self.root.after(100, self.refresh_tracking_analysis_panel)

    def refresh_tracking_http_status(self, silent=False, force=False):
        now = time.time()
        if self.tracking_http_refresh_inflight:
            return
        if not force and (now - self.tracking_last_http_refresh_ts) < TRACKING_MIN_HTTP_REFRESH_SECONDS:
            return

        self.tracking_http_refresh_inflight = True
        url = f"{self.tracking_http_base_url}/video/status/{self.tracking_match_id}"

        def worker():
            try:
                with urllib.request.urlopen(url, timeout=TRACKING_HTTP_TIMEOUT_SECONDS) as response:
                    data = json.loads(response.read().decode("utf-8"))
                self.root.after(
                    0,
                    lambda data=data, silent=silent: self._apply_tracking_http_status(data, silent),
                )
            except urllib.error.HTTPError as exc:
                error_text = f"HTTP {exc.code}"
                self.root.after(
                    0,
                    lambda error_text=error_text, silent=silent: self._apply_tracking_http_error(error_text, silent),
                )
            except Exception as exc:
                error_text = str(exc)
                self.root.after(
                    0,
                    lambda error_text=error_text, silent=silent: self._apply_tracking_http_error(error_text, silent),
                )
            finally:
                self.root.after(0, self._finish_tracking_http_refresh)

        threading.Thread(target=worker, daemon=True).start()

    def _finish_tracking_http_refresh(self):
        self.tracking_http_refresh_inflight = False
        self.tracking_last_http_refresh_ts = time.time()

    def _apply_tracking_http_status(self, data, silent):
        self.tracking_last_http_status = (
            f"registered={data.get('video_registered', False)} | "
            f"tracking={data.get('tracking_ready', False)} | "
            f"pitch_map={data.get('pitch_map_ready', False)} | "
            f"latest={data.get('latest_status', 'unknown')} | "
            f"subs={data.get('subscriber_count', 0)}"
        )
        self._render_tracking_state()
        self.refresh_tracking_analysis_panel()
        if not silent:
            self.add_commentary(f"Tracking status refreshed: {self.tracking_last_http_status}")

    def _apply_tracking_http_error(self, error_text, silent):
        self.tracking_last_http_status = f"error: {error_text}"
        self._render_tracking_state()
        self.refresh_tracking_analysis_panel()
        if not silent:
            self.add_commentary(f"Tracking status refresh failed: {error_text}")

    def _render_tracking_state(self):
        if hasattr(self, "tracking_match_label"):
            self.tracking_match_label.config(text=f"Match ID: {self.tracking_match_id}")
        if hasattr(self, "tracking_ws_label"):
            self.tracking_ws_label.config(text=f"WS: {self.tracking_ws_base_url}")
        if hasattr(self, "tracking_http_label"):
            self.tracking_http_label.config(text=f"HTTP: {self.tracking_http_base_url}")

        if hasattr(self, "tracking_socket_state_label"):
            socket_color = "#22c55e" if "connected" in self.tracking_last_status else "#facc15"
            lowered = self.tracking_last_status.lower()
            if "error" in lowered or "closed" in lowered:
                socket_color = "#f97316"
            self.tracking_socket_state_label.config(text=f"Socket: {self.tracking_last_status}", fg=socket_color)

        if hasattr(self, "tracking_event_label"):
            self.tracking_event_label.config(text=f"Last event: {self.tracking_last_message_type}")

        if hasattr(self, "tracking_video_status_label"):
            self.tracking_video_status_label.config(text=f"Video status: {self.tracking_last_http_status}")

    # ------------------------------------------------
    # BACKEND / DATA
    # ------------------------------------------------

    def startup_backend_then_load(self):
        self.add_commentary("Checking backend status...")
        run_in_background(self._ensure_backend_running, self._on_backend_ready, self._on_backend_error)

    def _ensure_backend_running(self):
        if self.backend_launcher.is_backend_running():
            return {"ready": True}
        return {"ready": self.backend_launcher.start_backend()}

    def _on_backend_ready(self, result):
        if result and result.get("ready"):
            self.backend_indicator.config(text="● Backend Online", fg="#22c55e")
            self.backend_online = True
            self.last_data_source = "backend"
        else:
            self.backend_indicator.config(text="● Offline / Cache Mode", fg="#f59e0b")
            self.backend_online = False
            self.last_data_source = "cache"

        self.load_initial_data()
        self.refresh_tracking_http_status(silent=True, force=True)
        self.refresh_tracking_analysis_panel()
        self.refresh_tracking_analysis_panel()
        self.start_tracking_subscription()

    def _on_backend_error(self, error):
        logger.exception("Backend startup error: %s", error)
        self.backend_indicator.config(text="● Offline / Cache Mode", fg="#f59e0b")
        self.backend_online = False
        self.last_data_source = "cache"
        self.load_initial_data()
        self.refresh_tracking_http_status(silent=True, force=True)
        self.refresh_tracking_analysis_panel()

    def load_initial_data(self):
        run_in_background(self._fetch_all_data, self._on_data_loaded, self._on_data_error)

    def _fetch_all_data(self):
        comp = self.current_competition
        return {
            "teams": self.data_client.load_teams(comp),
            "fixtures": self.data_client.load_fixtures(comp),
            "standings": self.data_client.load_standings(comp),
            "news": self.data_client.load_news(comp),
            "live_games": self.data_client.load_live_games(),
            "odds_markets": self.data_client.load_odds_markets(),
            "bet365_prematch": self.data_client.load_bet365_prematch(),
            "tournament_odds": self.data_client.load_odds_tournaments("17"),
        }

    def _extract_list_payload(self, payload):
        if isinstance(payload, list):
            return payload
        if isinstance(payload, dict):
            data = payload.get("data")
            if isinstance(data, list):
                return data
            if isinstance(data, dict):
                inner = data.get("items")
                if isinstance(inner, list):
                    return inner
        return []

    def _extract_dict_payload(self, payload):
        return payload if isinstance(payload, dict) else {}

    def _on_data_loaded(self, data):
        if not data:
            self.add_commentary("No data returned from backend.")
            return

        self.teams = self._extract_list_payload(data.get("teams"))
        self.fixtures = self._extract_list_payload(data.get("fixtures"))
        self.standings = self._extract_list_payload(data.get("standings"))
        self.news_items = self._extract_list_payload(data.get("news"))
        self.live_games = self._extract_dict_payload(data.get("live_games"))
        self.odds_markets = self._extract_dict_payload(data.get("odds_markets"))
        self.bet365_prematch = self._extract_dict_payload(data.get("bet365_prematch"))
        self.tournament_odds = self._extract_dict_payload(data.get("tournament_odds"))

        names = []
        for t in self.teams:
            if isinstance(t, dict):
                long_name = str(t.get("name", "")).strip()
                short_name = str(t.get("shortName", "")).strip()
                if long_name:
                    names.append(long_name)
                if short_name:
                    names.append(short_name)

        self.team_list = sorted(set(n for n in names if n))
        self.reload_selectors()
        self.refresh_all_display()
        self.populate_demo_pages()
        self.refresh_tracking_analysis_panel()
        self.add_commentary(f"Loaded {len(self.team_list)} teams for {self.current_competition}.")

    def _on_data_error(self, error):
        logger.exception("Data load error: %s", error)
        self.add_commentary("Failed to refresh backend data.")

    def schedule_live_refresh_loop(self):
        self.root.after(self.live_refresh_ms, self._live_refresh_wrapper)

    def _live_refresh_wrapper(self):
        self.load_initial_data()
        self.schedule_live_refresh_loop()

    def reload_selectors(self):
        self.home_box["values"] = self.team_list
        self.away_box["values"] = self.team_list

        if not self.team_list:
            self.home_box.set("")
            self.away_box.set("")
            return

        current_home = self.home_box.get().strip()
        current_away = self.away_box.get().strip()

        if current_home not in self.team_list:
            self.home_box.set(self.team_list[0])

        if current_away not in self.team_list:
            self.away_box.set(self.team_list[1] if len(self.team_list) > 1 else self.team_list[0])

        if self.home_box.get() == self.away_box.get() and len(self.team_list) > 1:
            self.away_box.set(self.team_list[1])

    # ------------------------------------------------
    # DISPLAY
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
        for attr in [
            "live_games_box",
            "scheduled_games_box",
            "bookmarked_games_box",
            "live_market_box",
            "scheduled_market_box",
            "selected_match_details_box",
            "match_history_context_box",
            "table_box",
            "match_data_box",
            "stats_summary_box",
        ]:
            if hasattr(self, attr):
                getattr(self, attr).delete("1.0", "end")

        live_matches = self.live_games.get("live_matches", []) if isinstance(self.live_games, dict) else []
        scheduled = self.live_games.get("scheduled_with_odds", []) if isinstance(self.live_games, dict) else []

        if hasattr(self, "live_games_box"):
            if live_matches:
                for m in live_matches[:10]:
                    self.live_games_box.insert(
                        "end",
                        f"{m.get('home','')} {m.get('score_home','?')}-{m.get('score_away','?')} {m.get('away','')}  {m.get('minute', m.get('status',''))}\n",
                    )
            else:
                self.live_games_box.insert("end", "No live ongoing games loaded.\n")

        if hasattr(self, "scheduled_games_box"):
            if scheduled:
                for m in scheduled[:10]:
                    self.scheduled_games_box.insert(
                        "end",
                        f"{m.get('home','')} vs {m.get('away','')}\n"
                        f"Kickoff: {self._format_kickoff(m)} | Status: {m.get('status','scheduled')}\n\n",
                    )
            else:
                self.scheduled_games_box.insert("end", "No scheduled games loaded.\n")

        if hasattr(self, "bookmarked_games_box"):
            bookmarked = self._build_bookmarked_games(scheduled)
            if bookmarked:
                for m in bookmarked:
                    self.bookmarked_games_box.insert(
                        "end",
                        f"{m.get('home','')} vs {m.get('away','')}\n"
                        f"Kickoff: {self._format_kickoff(m)}\n\n",
                    )
            else:
                self.bookmarked_games_box.insert("end", "No bookmarked scheduled games yet.\n")

        if hasattr(self, "live_market_box"):
            if live_matches:
                for m in live_matches[:8]:
                    self.live_market_box.insert(
                        "end",
                        f"{m.get('home','')} vs {m.get('away','')}\n"
                        f"H {m.get('home_odds', '-')} | D {m.get('draw_odds', '-')} | A {m.get('away_odds', '-')}\\n"
                        f"Minute: {m.get('minute', '-')} | Source: {m.get('source', 'live-feed')}\n\n",
                    )
            else:
                self.live_market_box.insert("end", "No live market odds available.\n")

        if hasattr(self, "scheduled_market_box"):
            if scheduled:
                for m in scheduled[:8]:
                    self.scheduled_market_box.insert(
                        "end",
                        f"{m.get('home','')} vs {m.get('away','')}\n"
                        f"H {m.get('home_odds', m.get('odds_home', '-'))} | D {m.get('draw_odds', m.get('odds_draw', '-'))} | A {m.get('away_odds', m.get('odds_away', '-'))}\n"
                        f"Kickoff: {self._format_kickoff(m)} | Source: {m.get('source', self.bet365_prematch.get('source', 'prematch')) if isinstance(self.bet365_prematch, dict) else 'prematch'}\n\n",
                    )
            else:
                self.scheduled_market_box.insert("end", "No scheduled market odds available.\n")

        selected_fixture = self._find_selected_fixture()
        if hasattr(self, "selected_match_details_box"):
            if selected_fixture:
                self.selected_match_details_box.insert(
                    "end",
                    f"Home: {selected_fixture.get('home','-')}\n"
                    f"Away: {selected_fixture.get('away','-')}\n"
                    f"Competition: {selected_fixture.get('competition', self.current_competition)}\n"
                    f"Date / Time: {self._format_kickoff(selected_fixture)}\n"
                    f"Venue: {selected_fixture.get('venue', selected_fixture.get('stadium', '-'))}\n"
                    f"Status: {selected_fixture.get('status', '-')}\n"
                    f"{self.prediction_engine.build_odds_caption(self.selected_fixture_odds)}\n"
                    f"Source: {selected_fixture.get('source', self.last_data_source)}\n"
                )
            else:
                self.selected_match_details_box.insert("end", "Select home and away teams to see the next incoming match details.\n")

        if hasattr(self, "match_history_context_box"):
            self.match_history_context_box.insert("end", self._build_history_context_text())

        if hasattr(self, "table_box"):
            if self.standings:
                for row in self.standings[:12]:
                    self.table_box.insert("end", f"{row.get('team','')}  Pts:{row.get('points',0)}\n")
            else:
                self.table_box.insert("end", "No standings loaded.\n")

        if hasattr(self, "match_data_box"):
            self.match_data_box.insert(
                "end",
                f"League: {self.current_competition}\n"
                f"Teams loaded: {len(self.team_list)}\n"
                f"Fixtures loaded: {len(self.fixtures)}\n"
                f"News loaded: {len(self.news_items)}\n"
                f"Live games: {len(live_matches)}\n"
                f"Scheduled games: {len(scheduled)}\n"
                f"Source: {self.last_data_source}\n",
            )

        if hasattr(self, "stats_summary_box"):
            self.stats_summary_box.insert("end", f"Prediction: {self.prediction_label.cget('text')}\n")
            self.stats_summary_box.insert("end", f"Odds: {self.prediction_engine.build_odds_caption(self.selected_fixture_odds)}\n")

        if hasattr(self, "market_box"):
            self.market_box.delete("1.0", "end")
            if isinstance(self.bet365_prematch, dict) and self.bet365_prematch:
                summary = self.bet365_prematch.get("summary", {}) or {}
                self.market_box.insert("end", "Prematch market\n")
                self.market_box.insert("end", f"Events: {summary.get('event_count', 0)}\n")
                self.market_box.insert("end", f"Source: {self.bet365_prematch.get('source', 'unknown')}\n")
            else:
                self.market_box.insert("end", "No market summary loaded.\n")

        self._render_selected_odds()

    def _format_kickoff(self, item):
        if not isinstance(item, dict):
            return "-"
        for key in ["start_time", "utcDate", "kickoff", "date", "datetime", "match_time"]:
            value = item.get(key)
            if value:
                return str(value)
        return "-"

    def _build_bookmarked_games(self, scheduled):
        scheduled = scheduled or []
        selected_home = self.home_box.get().strip() if hasattr(self, "home_box") else ""
        selected_away = self.away_box.get().strip() if hasattr(self, "away_box") else ""
        picks = []
        if selected_home and selected_away:
            for item in scheduled:
                if item.get("home") == selected_home and item.get("away") == selected_away:
                    picks.append(item)
                    break
        for item in scheduled[:5]:
            if item not in picks:
                picks.append(item)
        return picks[:5]

    def _find_selected_fixture(self):
        selected_home = self.home_box.get().strip() if hasattr(self, "home_box") else ""
        selected_away = self.away_box.get().strip() if hasattr(self, "away_box") else ""
        if not selected_home or not selected_away:
            return None

        scheduled = self.live_games.get("scheduled_with_odds", []) if isinstance(self.live_games, dict) else []
        for item in scheduled:
            if item.get("home") == selected_home and item.get("away") == selected_away:
                return {
                    "home": item.get("home"),
                    "away": item.get("away"),
                    "competition": item.get("competition", self.current_competition),
                    "status": item.get("status", "scheduled"),
                    "start_time": item.get("start_time", item.get("utcDate", "-")),
                    "venue": item.get("venue", item.get("stadium", "-")),
                    "source": item.get("source", "live_games"),
                }

        for item in self.fixtures:
            if not isinstance(item, dict):
                continue
            if item.get("home") == selected_home and item.get("away") == selected_away:
                return {
                    "home": item.get("home"),
                    "away": item.get("away"),
                    "competition": item.get("competition", self.current_competition),
                    "status": item.get("status", item.get("match_status", "-")),
                    "utcDate": item.get("utcDate", item.get("date", item.get("start_time", "-"))),
                    "venue": item.get("venue", item.get("stadium", "-")),
                    "source": item.get("source", "fixtures"),
                }
        return None

    def _recent_team_matches(self, team_name, limit=5):
        rows = []
        for item in self.fixtures:
            if not isinstance(item, dict):
                continue
            if team_name in (item.get("home"), item.get("away")):
                rows.append(item)
        return rows[:limit]

    def _build_history_context_text(self):
        selected_home = self.home_box.get().strip() if hasattr(self, "home_box") else ""
        selected_away = self.away_box.get().strip() if hasattr(self, "away_box") else ""
        if not selected_home and not selected_away:
            return "Select teams to view recent history context.\n"

        parts = []
        if selected_home:
            parts.append(f"{selected_home} recent matches")
            for item in self._recent_team_matches(selected_home, limit=5):
                parts.append(
                    f"- {item.get('home','')} {item.get('homeGoals', item.get('score_home','?'))}-{item.get('awayGoals', item.get('score_away','?'))} {item.get('away','')}  {item.get('status','')}"
                )
            parts.append("")
        if selected_away:
            parts.append(f"{selected_away} recent matches")
            for item in self._recent_team_matches(selected_away, limit=5):
                parts.append(
                    f"- {item.get('home','')} {item.get('homeGoals', item.get('score_home','?'))}-{item.get('awayGoals', item.get('score_away','?'))} {item.get('away','')}  {item.get('status','')}"
                )
            parts.append("")

        if selected_home and selected_away:
            parts.append("Recent head-to-head")
            count = 0
            for item in self.fixtures:
                if not isinstance(item, dict):
                    continue
                if (item.get("home") == selected_home and item.get("away") == selected_away) or (item.get("home") == selected_away and item.get("away") == selected_home):
                    parts.append(
                        f"- {item.get('home','')} {item.get('homeGoals', item.get('score_home','?'))}-{item.get('awayGoals', item.get('score_away','?'))} {item.get('away','')}  {item.get('status','')}"
                    )
                    count += 1
                    if count >= 5:
                        break
            if count == 0:
                parts.append("- No head-to-head rows found in current fixture cache.")

        return "\n".join(parts) + "\n"

    def populate_demo_pages(self):
        for box in [
            self.club_staff_box,
            self.club_history_box,
            self.club_fixtures_box,
            self.club_graph_box,
            self.club_player_stats_box,
            self.club_tactical_box,
            self.club_transfer_box,
            self.player_role_box,
            self.player_left_meta_box,
            self.player_attributes_box,
            self.player_info_box,
            self.player_season_box,
            self.player_career_box,
            self.post_latest_box,
            self.post_table_box,
        ]:
            box.delete("1.0", "end")

        team = self.home_box.get().strip() or "Club"
        self.team_overview_head.config(text=f"{team} Overview")
        self.player_head.config(text=f"{team} Player / Staff Stats")

        self.club_staff_box.insert("end", f"Manager: Head Coach\nClub: {team}\nReputation: High\n")
        self.club_history_box.insert("end", "Club history\nRecent trends\n")

        for row in self.fixtures[:10]:
            self.club_fixtures_box.insert("end", f"{row.get('home','')} vs {row.get('away','')}\n")

        self.club_graph_box.insert("end", "Ranking trend\nRevenue trend\n")
        self.club_player_stats_box.insert("end", "Top scorer\nMost assists\n")
        self.club_tactical_box.insert("end", "Formation: 4-3-3\nStyle: Positive\n")
        self.club_transfer_box.insert("end", "Transfers in/out\n")

        self.player_role_box.insert("end", "Role map\nPreferred positions\n")
        self.player_left_meta_box.insert("end", "Happiness: Good\nForm: Strong\n")
        for a in ["Crossing", "Dribbling", "Finishing", "Passing", "Pace", "Strength"]:
            self.player_attributes_box.insert("end", f"{a}: {random.randint(6, 20)}\n")
        self.player_info_box.insert("end", "Height: 185 cm\nPersonality: Determined\n")
        self.player_season_box.insert("end", "Apps: 0\nGoals: 0\n")
        self.player_career_box.insert("end", "Career totals\n")

        if self.fixtures:
            for row in self.fixtures[:8]:
                self.post_latest_box.insert("end", f"{row.get('home','')} vs {row.get('away','')}\n")
        if self.standings:
            for row in self.standings[:10]:
                self.post_table_box.insert("end", f"{row.get('team','')} {row.get('points',0)} pts\n")

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
        if home == away:
            self.add_commentary("Home and Away cannot be the same team.")
            return

        self.home_score = 0
        self.away_score = 0
        self.match_time = 0
        self.match_finished = False

        self.score_label.config(text="0 - 0")
        self.post_score_banner.config(text=f"{home} 0 - 0 {away}")
        self.engine.configure_match(home, away, home_form, away_form)

        run_in_background(
            lambda: {
                "home_form": self.data_client.load_team_form(home, self.current_competition),
                "away_form": self.data_client.load_team_form(away, self.current_competition),
                "selected_fixture_odds": self.data_client.load_selected_fixture_odds(home, away),
                "match_intelligence": self.data_client.load_match_intelligence(home, away, self.current_competition),
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
        result = result or {}

        self.home_form_data = result.get("home_form", {}) or {}
        self.away_form_data = result.get("away_form", {}) or {}
        self.selected_fixture_odds = result.get("selected_fixture_odds", {}) or {}

        intelligence = result.get("match_intelligence", {}) or {}
        self.team_advanced_form = intelligence.get("team_advanced_form", {}) or {}
        self.probable_lineups = intelligence.get("probable_lineups", {}) or {}
        self.injury_report = intelligence.get("injury_report", {}) or {}
        self.rest_profile = intelligence.get("rest_profile", {}) or {}
        self.odds_movement = intelligence.get("odds_movement", {}) or {}
        self.live_match_events = intelligence.get("live_match_events", {}) or {}
        self.player_form = intelligence.get("player_form", {}) or {}
        self.tactical_matchup = intelligence.get("tactical_matchup", {}) or {}

        prediction_text = self.prediction_engine.build_prediction(
            home=home,
            away=away,
            home_form=self.home_form_data,
            away_form=self.away_form_data,
            live_games=self.live_games,
            prematch_summary=self.bet365_prematch,
            tournament_odds=self.tournament_odds,
            fixture_odds=self.selected_fixture_odds,
            team_advanced_form=self.team_advanced_form,
            probable_lineups=self.probable_lineups,
            injury_report=self.injury_report,
            rest_profile=self.rest_profile,
            odds_movement=self.odds_movement,
            live_match_events=self.live_match_events,
            player_form=self.player_form,
            tactical_matchup=self.tactical_matchup,
        )

        prediction_block = self.prediction_engine.build_prediction_block(
            home=home,
            away=away,
            home_form=self.home_form_data,
            away_form=self.away_form_data,
            live_games=self.live_games,
            prematch_summary=self.bet365_prematch,
            tournament_odds=self.tournament_odds,
            fixture_odds=self.selected_fixture_odds,
            team_advanced_form=self.team_advanced_form,
            probable_lineups=self.probable_lineups,
            injury_report=self.injury_report,
            rest_profile=self.rest_profile,
            odds_movement=self.odds_movement,
            live_match_events=self.live_match_events,
            player_form=self.player_form,
            tactical_matchup=self.tactical_matchup,
        )

        self.prediction_last_block = prediction_block
        parts = prediction_text.split("|")
        self.prediction_last_verdict = parts[3].strip() if len(parts) >= 4 else "Likely winner: waiting"
        home_adv = self.team_advanced_form.get("home", {}) if isinstance(self.team_advanced_form, dict) else {}
        away_adv = self.team_advanced_form.get("away", {}) if isinstance(self.team_advanced_form, dict) else {}
        self.prediction_last_scoreline = (
            f"Scoreline tendency: {home} {round(float(home_adv.get('xg_for_5', home_adv.get('xg_for', 1.0)) or 1.0))} - "
            f"{round(float(away_adv.get('xg_for_5', away_adv.get('xg_for', 1.0)) or 1.0))} {away}"
        )
        self.post_match_summary_text = prediction_block

        self.prediction_label.config(text=prediction_text)
        self.form_label.config(
            text=(
                f"Team form\n"
                f"{home}: {' '.join(self.home_form_data.get('form_last5', [])) or 'n/a'}\n"
                f"{away}: {' '.join(self.away_form_data.get('form_last5', [])) or 'n/a'}"
            )
        )

        self.add_commentary(prediction_block)
        self.refresh_all_display()
        self.refresh_match_intelligence_panels()

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
        self.post_score_banner.config(text=f"{home} {self.home_score} - {self.away_score} {away}")
        self.add_commentary(f"Full time: {home} {self.home_score} - {self.away_score} {away}")

    # ------------------------------------------------
    # LOOPS
    # ------------------------------------------------

    def update_manager_tactics_loop(self):
        if hasattr(self, "engine") and self.engine.running and not self.match_finished:
            home_pos, away_pos = self.engine.get_possession_snapshot()
            self.tactic_label.config(
                text=(
                    f"Live tactics\n"
                    f"Home: {self.home_formation_box.get()}\n"
                    f"Away: {self.away_formation_box.get()}\n"
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
            self.live_match_detail.config(
                text=f"{self.home_box.get().strip() or 'Home'} vs {self.away_box.get().strip() or 'Away'} | {clock_text}"
            )
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
        self.post_score_banner.config(
            text=f"{self.home_box.get().strip() or 'Home'} {self.home_score} - {self.away_score} {self.away_box.get().strip() or 'Away'}"
        )
        self.add_commentary(self.commentary_engine.goal_commentary())

    def update_possession(self, home, away):
        self.possession_label.config(text=f"Possession {home}% - {away}%")

    # ------------------------------------------------
    # SETTINGS
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
            self.show_page("settings_home")
            self.add_commentary("Personalization applied.")
        except Exception as e:
            messagebox.showerror("Personalization", f"Could not apply settings:\n{e}")

    def choose_background(self, kind):
        path = filedialog.askopenfilename(
            title=f"Choose {kind} background",
            filetypes=[("Image files", "*.png *.jpg *.jpeg *.gif *.webp"), ("All files", "*.*")],
        )
        if not path:
            return

        if kind == "main":
            self.main_background_path = path
        elif kind == "general":
            self.general_background_path = path
        elif kind == "pitch":
            self.pitch_background_path = path
        elif kind == "stadium":
            self.stadium_background_path = path

        self.refresh_background_labels()
        self.apply_background_images()
        self._apply_full_page_background()
        self.add_commentary(f"{kind.title()} background set.")

    def apply_theme_to_widgets(self):
        self.root.configure(bg=self.theme_bg)
        self.main.configure(bg=self.theme_bg)
        self.page_host.configure(bg=self.theme_bg)

        self.app_title.configure(fg=self.text_fg)
        self.clock_top.configure(fg=self.text_fg)

        self.header_strip.configure(bg="#0d1422")
        self.home_logo_label.configure(bg="#0d1422", fg=self.text_fg)
        self.home_name_label.configure(bg="#0d1422", fg=self.text_fg, font=(self.font_family, self.header_font_size + 1, "bold"))
        self.score_label.configure(bg="#0d1422", fg=self.text_fg, font=(self.font_family, self.score_font_size + 6, "bold"))
        self.away_name_label.configure(bg="#0d1422", fg=self.text_fg, font=(self.font_family, self.header_font_size + 1, "bold"))
        self.away_logo_label.configure(bg="#0d1422", fg=self.text_fg)
        self.prediction_label.configure(bg="#0d1422", font=(self.font_family, self.body_font_size + 1, "bold"))
        self.backend_indicator.configure(bg="#0d1422")
        self.clock_label.configure(bg="#0d1422", fg=self.text_fg, font=(self.font_family, self.header_font_size + 8, "bold"))
        self.possession_label.configure(bg="#0d1422", fg=self.text_fg, font=(self.font_family, self.body_font_size))
        self.canvas.configure(bg=self.pitch_bg)

        self.refresh_background_labels()
        self.apply_background_images()
        self._apply_full_page_background()
        self._apply_button_hover_pack()

    def set_refresh_quality(self, mode):
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
    # TEAM / LOGO HELPERS
    # ------------------------------------------------

    def on_league_changed(self, _event=None):
        selected = self.league_box.get()
        self.current_competition = LEAGUE_OPTIONS.get(selected, "PL")

        self.team_list = []
        self.teams = []
        self.fixtures = []
        self.standings = []
        self.news_items = []
        self.live_games = {}
        self.bet365_prematch = {}
        self.tournament_odds = {}
        self.selected_fixture_odds = {}
        self.home_form_data = {}
        self.away_form_data = {}

        self.home_box.set("")
        self.away_box.set("")
        self.home_box["values"] = []
        self.away_box["values"] = []
        self.home_name_label.config(text="HOME")
        self.away_name_label.config(text="AWAY")
        self.prediction_label.config(text="Prediction: waiting")
        self.form_label.config(text="Team form: waiting")
        self.live_match_detail.config(text="Home vs Away | 00:00")

        self.add_commentary(f"League changed to {selected} ({self.current_competition}). Refreshing data...")
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
        self.selected_fixture_odds = data.get("selected_fixture_odds", {}) or {}
        self.home_form_data = data.get("home_form", {}) or {}
        self.away_form_data = data.get("away_form", {}) or {}
        self.refresh_all_display()

        home = self.home_box.get().strip()
        away = self.away_box.get().strip()
        if home and away and home != away:
            try:
                prediction_text = self.prediction_engine.build_prediction(
                    home=home,
                    away=away,
                    home_form=self.home_form_data,
                    away_form=self.away_form_data,
                    live_games=self.live_games,
                    prematch_summary=self.bet365_prematch,
                    tournament_odds=self.tournament_odds,
                    fixture_odds=self.selected_fixture_odds,
                    team_advanced_form=self.team_advanced_form,
                    probable_lineups=self.probable_lineups,
                    injury_report=self.injury_report,
                    rest_profile=self.rest_profile,
                    odds_movement=self.odds_movement,
                    live_match_events=self.live_match_events,
                    player_form=self.player_form,
                    tactical_matchup=self.tactical_matchup,
                )
                self.prediction_label.config(text=prediction_text)
                self.prediction_last_block = prediction_text
                parts = prediction_text.split("|")
                self.prediction_last_verdict = parts[3].strip() if len(parts) >= 4 else "Likely winner: waiting"
                self.refresh_match_intelligence_panels()
            except Exception as exc:
                logger.warning("Prediction update warning: %s", exc)

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

    def quit_app(self):
        if messagebox.askyesno("Quit", "Exit simulator?"):
            self.stop_tracking_subscription(silent=True)
            if self.tracking_status_loop_id is not None:
                try:
                    self.root.after_cancel(self.tracking_status_loop_id)
                except Exception:
                    pass
                self.tracking_status_loop_id = None
            self.root.destroy()


if __name__ == "__main__":
    root = tk.Tk()
    app = FootballSimulator(root)
    root.mainloop()