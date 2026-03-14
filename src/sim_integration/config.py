from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class SimulatorBackendConfig:
    base_url: str = os.getenv("BACKEND_BASE_URL", "http://127.0.0.1:8000")
    simulator_token: str = os.getenv("SIMULATOR_TOKEN", "change_me_simulator_token")
    competition: str = os.getenv("DEFAULT_COMPETITION", "PL")
    cache_dir: str = os.getenv("CACHE_DIR", "./cache")
    enable_http_fallback: bool = os.getenv("ENABLE_HTTP_FALLBACK", "true").lower() == "true"
    max_age_seconds: int = int(os.getenv("SIM_CACHE_MAX_AGE_SECONDS", "900"))
    http_timeout_seconds: float = float(os.getenv("HTTP_TIMEOUT_SECONDS", "1.8"))