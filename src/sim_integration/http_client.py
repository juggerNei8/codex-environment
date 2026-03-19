from __future__ import annotations

import json
import urllib.parse
import urllib.request
from typing import Any, Optional

from .config import SimulatorBackendConfig


class BackendHttpClient:
    def __init__(self, cfg: Optional[SimulatorBackendConfig] = None) -> None:
        self.cfg = cfg or SimulatorBackendConfig()

    def _resolve_base_url(self) -> str:
        base = getattr(self.cfg, "base_url", None)
        if not base:
            base = getattr(self.cfg, "backend_base_url", None)
        if not base:
            base = "http://127.0.0.1:8001"
        return str(base).rstrip("/")

    def _build_url(self, endpoint_path: str, params: Optional[dict] = None) -> str:
        base = self._resolve_base_url()
        endpoint = endpoint_path if endpoint_path.startswith("/") else f"/{endpoint_path}"
        url = f"{base}{endpoint}"

        if params:
            clean_params = {k: v for k, v in params.items() if v is not None}
            query = urllib.parse.urlencode(clean_params)
            if query:
                url = f"{url}?{query}"

        return url

    def _unwrap_payload(self, payload: Any) -> Any:
        if not isinstance(payload, dict):
            return payload
        if "data" in payload:
            return payload.get("data")
        return payload

    def get_data(self, endpoint_path: str, params: Optional[dict] = None) -> Any:
        url = self._build_url(endpoint_path, params=params)
        request = urllib.request.Request(
            url,
            headers={
                "X-Simulator-Token": self.cfg.simulator_token,
                "Accept": "application/json",
            },
            method="GET",
        )
        try:
            with urllib.request.urlopen(request, timeout=self.cfg.http_timeout_seconds) as response:
                raw = response.read().decode("utf-8")
                payload = json.loads(raw)
                return self._unwrap_payload(payload)
        except Exception:
            return None
