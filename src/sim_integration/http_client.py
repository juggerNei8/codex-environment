from __future__ import annotations

from typing import Any, Optional
import requests

from .config import SimulatorBackendConfig


class BackendHttpClient:
    def __init__(self, cfg: SimulatorBackendConfig) -> None:
        self.cfg = cfg

    def _headers(self) -> dict:
        token = (self.cfg.simulator_token or "").strip()
        headers = {"Accept": "application/json"}

        if token:
            headers["X-Simulator-Token"] = token

        return headers

    def get_data(self, path: str, params: Optional[dict] = None) -> Optional[Any]:
        if not self.cfg.enable_http_fallback:
            return None

        url = self.cfg.base_url.rstrip("/") + path
        try:
            r = requests.get(
                url,
                params=params,
                headers=self._headers(),
                timeout=self.cfg.http_timeout_seconds,
            )

            print(f"DEBUG HTTP GET {url} status={r.status_code}")

            payload = r.json() if "application/json" in (r.headers.get("content-type") or "") else None
            if not payload or not isinstance(payload, dict):
                return None

            if payload.get("success") is True:
                return payload.get("data")

            print("DEBUG backend payload failure:", payload)
            return None
        except Exception as e:
            print("DEBUG BackendHttpClient error:", repr(e))
            return None