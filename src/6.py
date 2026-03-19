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



class ScrollablePage(tk.Frame):
    def __init__(self, master, *, bg: str = "#000000", **kwargs):
        super().__init__(master, bg=bg, **kwargs)
        self.canvas = tk.Canvas(self, bg=bg, highlightthickness=0, bd=0, relief="flat")
        self.canvas.pack(fill="both", expand=True)
        self.content = tk.Frame(self.canvas, bg=bg)
        self.content_window = self.canvas.create_window((0, 0), window=self.content, anchor="nw")
        self.canvas.bind("<Configure>", self._on_canvas_configure)
        self.content.bind("<Configure>", self._on_content_configure)
        for widget in (self.canvas, self.content):
            widget.bind("<MouseWheel>", self._on_mousewheel, add="+")
            widget.bind("<Button-4>", self._on_mousewheel, add="+")
            widget.bind("<Button-5>", self._on_mousewheel, add="+")

    def _on_canvas_configure(self, event):
        self.canvas.itemconfigure(self.content_window, width=max(1, event.width))
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))

    def _on_content_configure(self, _event):
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))

    def _on_mousewheel(self, event):
        delta = 0
        if getattr(event, "delta", 0):
            delta = int(-1 * (event.delta / 120))
        elif getattr(event, "num", None) == 4:
            delta = -1
        elif getattr(event, "num", None) == 5:
            delta = 1
        if delta:
            self.canvas.yview_scroll(delta, "units")

    def scroll_to_top(self):
        self.canvas.yview_moveto(0.0)


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

    def (self, parent):
        self.match_center_container = self.make_card(parent, "Match Center")
        self.match_center_container.pack(fill="both", expand=True, pady=(0, 8))

        self.match_center_notebook = ttk.Notebook(self.match_center_container)
        self.match_center_notebook.pack(fill="both", expand=True)

        self.match_center_overview_tab = tk.Frame(self.match_center_notebook, bg=self.card_bg)
        self.match_center_notebook.add(self.match_center_overview_tab, text="Overview")

        self.match_center_history_tab = tk.Frame(self.match_center_notebook, bg=self.card_bg)
        self.match_center_notebook.add(self.match_center_history_tab, text="History")

        self.live_games_box = self._make_text_panel(self.match_center_overview_tab, "Live Ongoing Games", 6)
        self.scheduled_games_box = self._make_text_panel(self.match_center_overview_tab, "Scheduled Games", 6)
        self.bookmarked_games_box = self._make_text_panel(self.match_center_overview_tab, "Bookmarked Games", 5)
        self.selected_match_details_box = self._make_text_panel(self.match_center_overview_tab, "Selected Match Details", 6)
        self.history_context_box = self._make_text_panel(self.match_center_history_tab, "History Context", 12)

    def _fixture_datetime_text(self, fixture):
        value = ""
        if isinstance(fixture, dict):
            value = str(fixture.get("utcDate") or fixture.get("date") or fixture.get("start_time") or "").strip()
        return value or "unknown"

    def _find_selected_fixture(self, home, away):
        upcoming = None
        fallback = None
        for fx in self.fixtures or []:
            if not isinstance(fx, dict):
                continue
            fx_home = str(fx.get("home", "")).strip()
            fx_away = str(fx.get("away", "")).strip()
            if fx_home != home or fx_away != away:
                continue
            status = str(fx.get("status", "")).upper()
            if status not in {"FINISHED", "FT"} and upcoming is None:
                upcoming = fx
            if fallback is None:
                fallback = fx
        return upcoming or fallback or {}

    def _build_bookmarked_games(self):
        scheduled = self.live_games.get("scheduled_with_odds", []) if isinstance(self.live_games, dict) else []
        picks = []
        for row in scheduled[:5]:
            if isinstance(row, dict):
                picks.append(row)
        home = self.home_box.get().strip() if hasattr(self, "home_box") else ""
        away = self.away_box.get().strip() if hasattr(self, "away_box") else ""
        if home and away:
            picks.insert(0, {"home": home, "away": away, "status": "selected", "start_time": ""})
        self.bookmarked_games = picks[:5]

    def _build_match_history_context(self, home, away):
        home_recent = []
        away_recent = []
        h2h = []
        for fx in self.fixtures or []:
            if not isinstance(fx, dict):
                continue
            fx_home = str(fx.get("home", "")).strip()
            fx_away = str(fx.get("away", "")).strip()
            if home in (fx_home, fx_away):
                home_recent.append(fx)
            if away in (fx_home, fx_away):
                away_recent.append(fx)
            if {home, away} == {fx_home, fx_away}:
                h2h.append(fx)
        self.match_history_context = {
            "home_recent": home_recent[:5],
            "away_recent": away_recent[:5],
            "h2h": h2h[:5],
        }

    def refresh_match_center_panels(self):
        home = self.home_box.get().strip() if hasattr(self, "home_box") else ""
        away = self.away_box.get().strip() if hasattr(self, "away_box") else ""

        self._build_bookmarked_games()
        selected_fx = self._find_selected_fixture(home, away) if home and away else {}
        self.selected_match_details = selected_fx or {}
        if home and away:
            self._build_match_history_context(home, away)

        if hasattr(self, "live_games_box"):
            self.live_games_box.delete("1.0", "end")
            live_matches = self.live_games.get("live_matches", []) if isinstance(self.live_games, dict) else []
            if live_matches:
                for row in live_matches[:10]:
                    self.live_games_box.insert(
                        "end",
                        f"{row.get('home','')} {row.get('score_home','?')}-{row.get('score_away','?')} {row.get('away','')}  {row.get('minute','')}\n",
                    )
            else:
                self.live_games_box.insert("end", "No live ongoing games loaded.\n")

        if hasattr(self, "scheduled_games_box"):
            self.scheduled_games_box.delete("1.0", "end")
            scheduled = self.live_games.get("scheduled_with_odds", []) if isinstance(self.live_games, dict) else []
            if scheduled:
                for row in scheduled[:10]:
                    self.scheduled_games_box.insert(
                        "end",
                        f"{row.get('home','')} vs {row.get('away','')} | {row.get('status','')} | {row.get('start_time','')}\n",
                    )
            else:
                self.scheduled_games_box.insert("end", "No scheduled games loaded.\n")

        if hasattr(self, "bookmarked_games_box"):
            self.bookmarked_games_box.delete("1.0", "end")
            if self.bookmarked_games:
                for row in self.bookmarked_games:
                    self.bookmarked_games_box.insert(
                        "end",
                        f"{row.get('home','')} vs {row.get('away','')} | {row.get('status','')} | {row.get('start_time','')}\n",
                    )
            else:
                self.bookmarked_games_box.insert("end", "No bookmarked games yet.\n")

        if hasattr(self, "selected_match_details_box"):
            self.selected_match_details_box.delete("1.0", "end")
            if self.selected_match_details:
                fx = self.selected_match_details
                self.selected_match_details_box.insert("end", f"Home: {fx.get('home', home)}\n")
                self.selected_match_details_box.insert("end", f"Away: {fx.get('away', away)}\n")
                self.selected_match_details_box.insert("end", f"Competition: {self.current_competition}\n")
                self.selected_match_details_box.insert("end", f"Date/Time: {self._fixture_datetime_text(fx)}\n")
                self.selected_match_details_box.insert("end", f"Status: {fx.get('status', 'unknown')}\n")
                self.selected_match_details_box.insert("end", f"Venue: {fx.get('venue', fx.get('stadium', 'unknown'))}\n")
                self.selected_match_details_box.insert("end", f"{self.prediction_engine.build_odds_caption(self.selected_fixture_odds)}\n")
            else:
                self.selected_match_details_box.insert("end", "Select teams to view incoming match details.\n")

        if hasattr(self, "history_context_box"):
            self.history_context_box.delete("1.0", "end")
            if self.match_history_context:
                self.history_context_box.insert("end", "Home recent:\n")
                for fx in self.match_history_context.get("home_recent", []):
                    self.history_context_box.insert("end", f"- {fx.get('home','')} vs {fx.get('away','')} | {fx.get('status','')} | {self._fixture_datetime_text(fx)}\n")
                self.history_context_box.insert("end", "\nAway recent:\n")
                for fx in self.match_history_context.get("away_recent", []):
                    self.history_context_box.insert("end", f"- {fx.get('home','')} vs {fx.get('away','')} | {fx.get('status','')} | {self._fixture_datetime_text(fx)}\n")
                self.history_context_box.insert("end", "\nHead-to-head:\n")
                for fx in self.match_history_context.get("h2h", []):
                    self.history_context_box.insert("end", f"- {fx.get('home','')} vs {fx.get('away','')} | {fx.get('status','')} | {self._fixture_datetime_text(fx)}\n")
            else:
                self.history_context_box.insert("end", "History context waiting.\n")

    def refresh_match_intelligence_panels(self):
        if hasattr(self, "prediction_summary_box"):
            self.prediction_summary_box.delete("1.0", "end")
            self.prediction_summary_box.insert("end", (self.prediction_last_block or self.prediction_label.cget("text")) + "\n")
        if hasattr(self, "verdict_box"):
            self.verdict_box.delete("1.0", "end")
            self.verdict_box.insert("end", (self.prediction_last_verdict or "Likely winner: waiting") + "\n")
        if hasattr(self, "scoreline_box"):
            self.scoreline_box.delete("1.0", "end")
            self.scoreline_box.insert("end", (self.prediction_last_scoreline or "Scoreline tendency: waiting") + "\n")
        self.refresh_above_fold_panels()

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
            for line in [
                f"Home formation: {home_line.get('formation', '-')}",
                f"Home strength: {home_line.get('strength_score', '-')}",
                f"Away formation: {away_line.get('formation', '-')}",
                f"Away strength: {away_line.get('strength_score', '-')}",
                f"Home missing key: {home_line.get('key_absent_count', '-')}",
                f"Away missing key: {away_line.get('key_absent_count', '-')}",
            ]:
                self.lineup_box.insert("end", line + "\n")

        if hasattr(self, "injuries_box"):
            self.injuries_box.delete("1.0", "end")
            home_inj = self.injury_report.get("home", {}) if isinstance(self.injury_report, dict) else {}
            away_inj = self.injury_report.get("away", {}) if isinstance(self.injury_report, dict) else {}
            for line in [
                f"Home injury impact: {home_inj.get('impact_score', '-')}",
                f"Home injured: {home_inj.get('injured_count', '-')}",
                f"Home suspended: {home_inj.get('suspended_count', '-')}",
                f"Away injury impact: {away_inj.get('impact_score', '-')}",
                f"Away injured: {away_inj.get('injured_count', '-')}",
                f"Away suspended: {away_inj.get('suspended_count', '-')}",
            ]:
                self.injuries_box.insert("end", line + "\n")

        if hasattr(self, "fatigue_box"):
            self.fatigue_box.delete("1.0", "end")
            home_rest = self.rest_profile.get("home", {}) if isinstance(self.rest_profile, dict) else {}
            away_rest = self.rest_profile.get("away", {}) if isinstance(self.rest_profile, dict) else {}
            for line in [
                f"Home days rest: {home_rest.get('days_rest', '-')}",
                f"Home fatigue: {home_rest.get('fatigue_score', '-')}",
                f"Away days rest: {away_rest.get('days_rest', '-')}",
                f"Away fatigue: {away_rest.get('fatigue_score', '-')}",
            ]:
                self.fatigue_box.insert("end", line + "\n")

        if hasattr(self, "market_box"):
            self.market_box.delete("1.0", "end")
            self.market_box.insert("end", f"Direction: {self.odds_movement.get('direction', '-')}\n")
            self.market_box.insert("end", f"Home move %: {self.odds_movement.get('home_move_pct', '-')}\n")
            self.market_box.insert("end", f"Away move %: {self.odds_movement.get('away_move_pct', '-')}\n")
            self.market_box.insert("end", self.prediction_engine.build_odds_caption(self.selected_fixture_odds) + "\n")

        if hasattr(self, "tactical_box"):
            self.tactical_box.delete("1.0", "end")
            self.tactical_box.insert("end", f"Home tactical edge: {self.tactical_matchup.get('home_edge_score', '-')}\n")
            self.tactical_box.insert("end", f"Away tactical edge: {self.tactical_matchup.get('away_edge_score', '-')}\n")
            for note in (self.tactical_matchup.get("notes", []) if isinstance(self.tactical_matchup, dict) else [])[:4]:
                self.tactical_box.insert("end", f"- {note}\n")

        if hasattr(self, "player_form_box"):
            self.player_form_box.delete("1.0", "end")
            home_pf = self.player_form.get("home", {}) if isinstance(self.player_form, dict) else {}
            away_pf = self.player_form.get("away", {}) if isinstance(self.player_form, dict) else {}
            for line in [
                f"Home attack form: {home_pf.get('attack_form', '-')}",
                f"Home defense form: {home_pf.get('defense_form', '-')}",
                f"Away attack form: {away_pf.get('attack_form', '-')}",
                f"Away defense form: {away_pf.get('defense_form', '-')}",
            ]:
                self.player_form_box.insert("end", line + "\n")

        if hasattr(self, "post_prediction_box"):
            self.post_prediction_box.delete("1.0", "end")
            self.post_prediction_box.insert("end", (self.post_match_summary_text or "Post-match intelligence waiting") + "\n")

        self.refresh_match_center_panels()

    def refresh_match_center_panels(self):
        home = self.home_box.get().strip() if hasattr(self, "home_box") else ""
        away = self.away_box.get().strip() if hasattr(self, "away_box") else ""
        live_matches = self.live_games.get("live_matches", []) if isinstance(self.live_games, dict) else []
        scheduled = self.live_games.get("scheduled_with_odds", []) if isinstance(self.live_games, dict) else []

        if hasattr(self, "bookmarked_games_box"):
            self.bookmarked_games_box.delete("1.0", "end")
            picks = scheduled[:5]
            if picks:
                for m in picks:
                    self.bookmarked_games_box.insert("end", f"{m.get('home','')} vs {m.get('away','')} | {m.get('start_time', m.get('utcDate',''))}\n")
            else:
                self.bookmarked_games_box.insert("end", "No scheduled bookmarked games.\n")

        if hasattr(self, "scheduled_games_box"):
            self.scheduled_games_box.delete("1.0", "end")
            if scheduled:
                for m in scheduled[:10]:
                    self.scheduled_games_box.insert("end", f"{m.get('home','')} vs {m.get('away','')} | {m.get('status','')} | {m.get('start_time', m.get('utcDate',''))}\n")
            else:
                self.scheduled_games_box.insert("end", "No scheduled games loaded.\n")

        if hasattr(self, "live_market_box"):
            self.live_market_box.delete("1.0", "end")
            if live_matches:
                for m in live_matches[:8]:
                    self.live_market_box.insert("end", f"{m.get('home','')} vs {m.get('away','')} | {m.get('minute','')} | H {m.get('home_odds','-')} D {m.get('draw_odds','-')} A {m.get('away_odds','-')}\n")
            else:
                self.live_market_box.insert("end", "No live market odds loaded.\n")

        if hasattr(self, "scheduled_market_box"):
            self.scheduled_market_box.delete("1.0", "end")
            if scheduled:
                for m in scheduled[:8]:
                    self.scheduled_market_box.insert("end", f"{m.get('home','')} vs {m.get('away','')} | H {m.get('home_odds','-')} D {m.get('draw_odds','-')} A {m.get('away_odds','-')}\n")
            else:
                self.scheduled_market_box.insert("end", "No scheduled market odds loaded.\n")

        if hasattr(self, "selected_match_details_box"):
            self.selected_match_details_box.delete("1.0", "end")
            match = None
            for fx in self.fixtures or []:
                if str(fx.get('home','')).strip() == home and str(fx.get('away','')).strip() == away:
                    match = fx
                    break
            if home and away:
                self.selected_match_details_box.insert("end", f"Home: {home}\nAway: {away}\nCompetition: {self.current_competition}\n")
                if match:
                    self.selected_match_details_box.insert("end", f"Date: {match.get('utcDate', '-')}\nStatus: {match.get('status', '-')}\nVenue: {match.get('venue', match.get('stadium','-'))}\n")
                self.selected_match_details_box.insert("end", self.prediction_engine.build_odds_caption(self.selected_fixture_odds) + "\n")
            else:
                self.selected_match_details_box.insert("end", "Select home and away teams to view match details.\n")

        if hasattr(self, "match_history_context_box"):
            self.match_history_context_box.delete("1.0", "end")
            if home or away:
                self.match_history_context_box.insert("end", f"{home} recent: {' '.join(self.home_form_data.get('form_last5', [])) or 'n/a'}\n")
                self.match_history_context_box.insert("end", f"{away} recent: {' '.join(self.away_form_data.get('form_last5', [])) or 'n/a'}\n")
                self.match_history_context_box.insert("end", f"{home} GF/GA: {self.home_form_data.get('goals_for_recent', '-')} / {self.home_form_data.get('goals_against_recent', '-')}\n")
                self.match_history_context_box.insert("end", f"{away} GF/GA: {self.away_form_data.get('goals_for_recent', '-')} / {self.away_form_data.get('goals_against_recent', '-')}\n")
            else:
                self.match_history_context_box.insert("end", "No selected matchup history context yet.\n")

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
        self.prediction_last_verdict = self.extract_prediction_verdict(prediction_text)
        self.prediction_last_scoreline = self.build_scoreline_tendency(home, away)
        self.post_match_summary_text = self.build_post_match_summary()

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
        self.team_advanced_form = {}
        self.probable_lineups = {}
        self.injury_report = {}
        self.rest_profile = {}
        self.odds_movement = {}
        self.live_match_events = {}
        self.player_form = {}
        self.tactical_matchup = {}
        self.prediction_last_block = ""
        self.prediction_last_scoreline = "Scoreline tendency: waiting"
        self.prediction_last_verdict = "Likely winner: waiting"
        self.post_match_summary_text = "Post-match intelligence waiting"

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

        intelligence = data.get("match_intelligence", {}) or {}
        self.team_advanced_form = intelligence.get("team_advanced_form", {}) or {}
        self.probable_lineups = intelligence.get("probable_lineups", {}) or {}
        self.injury_report = intelligence.get("injury_report", {}) or {}
        self.rest_profile = intelligence.get("rest_profile", {}) or {}
        self.odds_movement = intelligence.get("odds_movement", {}) or {}
        self.live_match_events = intelligence.get("live_match_events", {}) or {}
        self.player_form = intelligence.get("player_form", {}) or {}
        self.tactical_matchup = intelligence.get("tactical_matchup", {}) or {}

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
                self.prediction_last_verdict = self.extract_prediction_verdict(prediction_text)
                self.prediction_last_scoreline = self.build_scoreline_tendency(home, away)
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