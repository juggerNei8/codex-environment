from __future__ import annotations

import os
import subprocess
import sys
import time
from pathlib import Path

import requests

from logging_helper import get_logger


logger = get_logger("backend_launcher", "backend_launcher.log")


class BackendLauncher:
    def __init__(self) -> None:
        self.backend_base_url = os.getenv("BACKEND_BASE_URL", "http://127.0.0.1:8001").rstrip("/")
        self.backend_port = self._extract_port(self.backend_base_url)
        self.backend_project_dir = Path(os.getenv("BACKEND_PROJECT_DIR", r"C:\Project X\football-gateway"))
        self.backend_command = [
            sys.executable,
            "-m",
            "uvicorn",
            "app.main:app",
            "--host",
            "0.0.0.0",
            "--port",
            str(self.backend_port),
        ]
        self.process: subprocess.Popen | None = None

    def _extract_port(self, base_url: str) -> int:
        try:
            return int(base_url.rsplit(":", 1)[-1])
        except Exception:
            return 8001

    def health_url(self) -> str:
        return f"{self.backend_base_url}/api/health"

    def is_backend_running(self, timeout: float = 1.0) -> bool:
        try:
            r = requests.get(self.health_url(), timeout=timeout)
            return r.status_code == 200
        except Exception:
            return False

    def wait_until_ready(self, retries: int = 20, delay: float = 1.0) -> bool:
        for _ in range(retries):
            if self.is_backend_running(timeout=1.5):
                logger.info("Backend health check OK.")
                return True
            time.sleep(delay)
        logger.warning("Backend did not become ready in time.")
        return False

    def start_backend(self) -> bool:
        if self.is_backend_running():
            logger.info("Backend already running.")
            return True

        if not self.backend_project_dir.exists():
            logger.error("Backend project directory not found: %s", self.backend_project_dir)
            return False

        logger.info("Starting backend from %s", self.backend_project_dir)

        try:
            logs_dir = Path(__file__).resolve().parent / "logs"
            logs_dir.mkdir(parents=True, exist_ok=True)
            backend_log = open(logs_dir / "backend_runtime.log", "a", encoding="utf-8")

            creationflags = 0
            if os.name == "nt":
                creationflags = subprocess.CREATE_NO_WINDOW

            self.process = subprocess.Popen(
                self.backend_command,
                cwd=str(self.backend_project_dir),
                stdout=backend_log,
                stderr=backend_log,
                creationflags=creationflags,
            )
        except Exception as e:
            logger.exception("Failed to start backend: %s", e)
            return False

        return self.wait_until_ready()

    def stop_backend(self) -> None:
        if self.process and self.process.poll() is None:
            logger.info("Stopping backend process.")
            self.process.terminate()
            try:
                self.process.wait(timeout=5)
            except Exception:
                self.process.kill()