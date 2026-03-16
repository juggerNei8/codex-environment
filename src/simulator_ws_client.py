import json
import threading
import time
from typing import Any, Callable, Dict, Optional

try:
    import websocket  # websocket-client
except ImportError as exc:  # pragma: no cover
    raise ImportError(
        "websocket-client is required. Install it with: pip install websocket-client"
    ) from exc


MessageHandler = Callable[[Dict[str, Any]], None]
StatusHandler = Callable[[str], None]
ErrorHandler = Callable[[Exception], None]


class SimulatorLiveClient:
    """
    Drop-in WebSocket client for subscribing to live match updates from simvision_api.

    What it does:
    - connects to /realtime/ws/{match_id}
    - keeps the connection alive in a background thread
    - auto-reconnects when the server drops
    - forwards parsed JSON messages to your callback

    Where to use it:
    - inside the simulator dashboard controller
    - inside any live match monitor module

    Why it matters:
    - lets simulator.exe receive push updates instead of polling repeatedly
    """

    def __init__(
        self,
        ws_base_url: str,
        match_id: str,
        on_message: Optional[MessageHandler] = None,
        on_status: Optional[StatusHandler] = None,
        on_error: Optional[ErrorHandler] = None,
        reconnect_delay: float = 3.0,
        heartbeat_timeout: float = 30.0,
    ) -> None:
        self.ws_base_url = ws_base_url.rstrip("/")
        self.match_id = match_id
        self.on_message = on_message or self._default_message_handler
        self.on_status = on_status or self._default_status_handler
        self.on_error = on_error or self._default_error_handler
        self.reconnect_delay = reconnect_delay
        self.heartbeat_timeout = heartbeat_timeout

        self._ws: Optional[websocket.WebSocketApp] = None
        self._thread: Optional[threading.Thread] = None
        self._running = False
        self._last_message_at = 0.0
        self._lock = threading.Lock()

    @property
    def ws_url(self) -> str:
        return f"{self.ws_base_url}/realtime/ws/{self.match_id}"

    def start(self) -> None:
        """Start the client in a background thread."""
        with self._lock:
            if self._running:
                return
            self._running = True

        self._thread = threading.Thread(target=self._run_forever, daemon=True)
        self._thread.start()
        self.on_status(f"starting: {self.ws_url}")

    def stop(self) -> None:
        """Stop the client cleanly."""
        with self._lock:
            self._running = False

        if self._ws is not None:
            try:
                self._ws.close()
            except Exception:
                pass

        self.on_status("stopped")

    def is_running(self) -> bool:
        with self._lock:
            return self._running

    def _run_forever(self) -> None:
        while self.is_running():
            try:
                self._connect_once()
            except Exception as exc:
                self.on_error(exc)

            if self.is_running():
                self.on_status(f"reconnecting in {self.reconnect_delay:.1f}s")
                time.sleep(self.reconnect_delay)

    def _connect_once(self) -> None:
        self._last_message_at = time.time()

        def _on_open(ws: websocket.WebSocketApp) -> None:
            self.on_status(f"connected: {self.match_id}")
            self._last_message_at = time.time()

        def _on_message(ws: websocket.WebSocketApp, message: str) -> None:
            self._last_message_at = time.time()
            payload = self._parse_message(message)
            self.on_message(payload)

        def _on_error(ws: websocket.WebSocketApp, error: Any) -> None:
            if isinstance(error, Exception):
                self.on_error(error)
            else:
                self.on_error(Exception(str(error)))

        def _on_close(
            ws: websocket.WebSocketApp,
            close_status_code: Optional[int],
            close_msg: Optional[str],
        ) -> None:
            self.on_status(
                f"disconnected: code={close_status_code}, reason={close_msg or 'n/a'}"
            )

        self._ws = websocket.WebSocketApp(
            self.ws_url,
            on_open=_on_open,
            on_message=_on_message,
            on_error=_on_error,
            on_close=_on_close,
        )

        heartbeat_thread = threading.Thread(target=self._heartbeat_watchdog, daemon=True)
        heartbeat_thread.start()

        self._ws.run_forever(ping_interval=15, ping_timeout=5)

    def _heartbeat_watchdog(self) -> None:
        while self.is_running() and self._ws is not None:
            time.sleep(5)
            elapsed = time.time() - self._last_message_at
            if elapsed > self.heartbeat_timeout:
                self.on_status("heartbeat timeout reached, closing socket")
                try:
                    self._ws.close()
                except Exception:
                    pass
                return

    @staticmethod
    def _parse_message(message: str) -> Dict[str, Any]:
        try:
            payload = json.loads(message)
            if isinstance(payload, dict):
                return payload
            return {"type": "raw", "payload": payload}
        except json.JSONDecodeError:
            return {"type": "raw", "payload": message}

    @staticmethod
    def _default_message_handler(payload: Dict[str, Any]) -> None:
        print("[live-update]", json.dumps(payload, indent=2, ensure_ascii=False))

    @staticmethod
    def _default_status_handler(status: str) -> None:
        print(f"[ws-status] {status}")

    @staticmethod
    def _default_error_handler(error: Exception) -> None:
        print(f"[ws-error] {error}")


def subscribe_to_live_updates(
    ws_base_url: str,
    match_id: str,
    on_message: Optional[MessageHandler] = None,
    on_status: Optional[StatusHandler] = None,
    on_error: Optional[ErrorHandler] = None,
) -> SimulatorLiveClient:
    """
    Convenience wrapper for immediate simulator use.

    Example:
        client = subscribe_to_live_updates(
            "ws://127.0.0.1:8000",
            "video_demo",
            on_message=handle_live_message,
        )
    """
    client = SimulatorLiveClient(
        ws_base_url=ws_base_url,
        match_id=match_id,
        on_message=on_message,
        on_status=on_status,
        on_error=on_error,
    )
    client.start()
    return client
