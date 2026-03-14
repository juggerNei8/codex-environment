import os
import sys
import time
import subprocess
from pathlib import Path

import requests


class BackendLauncher:
    def __init__(self):
        self.backend_base_url = os.getenv("BACKEND_BASE_URL", "http://127.0.0.1:8000")
        self.health_url = self.backend_base_url.rstrip("/") + "/api/health"
        self.backend_root = self._resolve_backend_root()
        self.backend_process = None

    def _resolve_backend_root(self) -> Path:
        src_dir = Path(__file__).resolve().parent
        project_root = src_dir.parent
        candidate = project_root.parent / "football-gateway"

        if candidate.exists():
            return candidate

        env_path = os.getenv("BACKEND_ROOT", "").strip()
        if env_path:
            env_candidate = Path(env_path)
            if env_candidate.exists():
                return env_candidate

        return candidate

    def is_backend_running(self) -> bool:
        try:
            r = requests.get(self.health_url, timeout=2.5)
            return r.status_code == 200
        except Exception:
            return False

    def start_backend(self) -> bool:
        if self.is_backend_running():
            return True

        if not self.backend_root.exists():
            raise RuntimeError(f"Backend root not found: {self.backend_root}")

        python_exe = sys.executable
        env = os.environ.copy()
        env["PYTHONUNBUFFERED"] = "1"

        creationflags = 0
        if os.name == "nt":
            creationflags = subprocess.CREATE_NEW_PROCESS_GROUP

        self.backend_process = subprocess.Popen(
            [
                python_exe,
                "-m",
                "uvicorn",
                "app.main:app",
                "--host",
                "0.0.0.0",
                "--port",
                "8000",
            ],
            cwd=str(self.backend_root),
            env=env,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            creationflags=creationflags,
        )

        return self.wait_until_ready(timeout_seconds=25)

    def wait_until_ready(self, timeout_seconds: int = 25) -> bool:
        start = time.time()
        while time.time() - start < timeout_seconds:
            if self.is_backend_running():
                return True
            time.sleep(1.0)
        return False