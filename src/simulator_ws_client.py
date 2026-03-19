import json
import threading
import time
from typing import Callable, Optional

import websocket


class SimulatorWebSocketClient:
    """
    Live update client for the simulator.

    What it does:
    - Connects to the analytics API WebSocket endpoint
    - Receives JSON live updates
    - Reconnects automatically if disconnected
    - Runs in a background thread
    """

    def __init__(
        self,
        ws_base_url: str,
        match_id: str,
        on_message: Optional[Callable[[dict], None]] = None,
        on_status: Optional[Callable[[str], None]] = None,
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

    def _notify_status(self, status: str) -> None:
        if self.on_status:
            try:
                self.on_status(status)
            except Exception as exc:
                print(f"[ws-status-callback-error] {exc}")
        else:
            print(f"[ws-status] {status}")

    def _handle_message(self, message: str) -> None:
        try:
            payload = json.loads(message)
        except json.JSONDecodeError:
            payload = {"type": "raw_message", "message": message}

        if self.on_message:
            try:
                self.on_message(payload)
            except Exception as exc:
                print(f"[ws-message-callback-error] {exc}")
        else:
            print("[ws-message]", payload)

    def _build_ws_url(self) -> str:
        return f"{self.ws_base_url}/realtime/ws/{self.match_id}"

    def _run_forever(self) -> None:
        while not self._stop_event.is_set():
            ws_url = self._build_ws_url()
            self._notify_status(f"connecting -> {ws_url}")

            try:
                self.ws = websocket.WebSocketApp(
                    ws_url,
                    on_open=self._on_open,
                    on_message=self._on_message,
                    on_error=self._on_error,
                    on_close=self._on_close,
                )
                self.ws.run_forever()
            except Exception as exc:
                self._notify_status(f"connection exception: {exc}")

            if not self._stop_event.is_set():
                self._notify_status(
                    f"disconnected, retrying in {self.reconnect_delay} seconds"
                )
                time.sleep(self.reconnect_delay)

    def _on_open(self, ws):
        self._connected = True
        self._notify_status("connected")

    def _on_message(self, ws, message):
        self._handle_message(message)

    def _on_error(self, ws, error):
        self._connected = False
        self._notify_status(f"error: {error}")

    def _on_close(self, ws, close_status_code, close_msg):
        self._connected = False
        self._notify_status(
            f"closed: code={close_status_code}, message={close_msg}"
        )

    def start(self) -> None:
        if self.thread and self.thread.is_alive():
            self._notify_status("already running")
            return

        self._stop_event.clear()
        self.thread = threading.Thread(target=self._run_forever, daemon=True)
        self.thread.start()
        self._notify_status("background listener started")

    def stop(self) -> None:
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


def subscribe_to_live_updates(
    ws_base_url: str,
    match_id: str,
    on_message: Optional[Callable[[dict], None]] = None,
    on_status: Optional[Callable[[str], None]] = None,
) -> SimulatorWebSocketClient:
    """
    Convenience helper.

    Example:
        client = subscribe_to_live_updates(
            ws_base_url="ws://127.0.0.1:8000",
            match_id="video_demo",
            on_message=handle_live_message,
            on_status=handle_ws_status,
        )
    """
    client = SimulatorWebSocketClient(
        ws_base_url=ws_base_url,
        match_id=match_id,
        on_message=on_message,
        on_status=on_status,
    )
    client.start()
    return client