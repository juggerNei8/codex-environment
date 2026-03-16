from __future__ import annotations

import os
import sys
import tkinter as tk
from tkinter import messagebox

from backend_launcher import BackendLauncher
from logging_helper import get_logger

logger = get_logger("run_simulator", "run_simulator.log")


def validate_environment() -> list[str]:
    issues: list[str] = []

    backend_url = os.getenv("BACKEND_BASE_URL", "http://127.0.0.1:8001")
    cache_dir = os.getenv("CACHE_DIR", r"C:\Project X\football-gateway\cache")
    backend_dir = os.getenv("BACKEND_PROJECT_DIR", r"C:\Project X\football-gateway")

    if not backend_url.startswith("http"):
        issues.append("BACKEND_BASE_URL is invalid.")

    if not os.path.isdir(backend_dir):
        issues.append(f"Backend project folder missing: {backend_dir}")

    if not os.path.isdir(cache_dir):
        issues.append(f"Cache folder missing: {cache_dir}")

    return issues


def main() -> int:
    os.environ.setdefault("SIMULATOR_TOKEN", "change_me_simulator_token")
    os.environ.setdefault("BACKEND_BASE_URL", "http://127.0.0.1:8001")
    os.environ.setdefault("ENABLE_HTTP_FALLBACK", "true")
    os.environ.setdefault("CACHE_DIR", r"C:\Project X\football-gateway\cache")
    os.environ.setdefault("BACKEND_PROJECT_DIR", r"C:\Project X\football-gateway")

    issues = validate_environment()
    if issues:
        root = tk.Tk()
        root.withdraw()
        messagebox.showwarning(
            "Startup check",
            "Some startup checks failed:\n\n" + "\n".join(f"- {x}" for x in issues) +
            "\n\nThe simulator will still try to run."
        )
        root.destroy()

    launcher = BackendLauncher()

    if not launcher.is_backend_running():
        logger.info("Backend not running. Attempting auto-start.")
        ok = launcher.start_backend()
        if not ok:
            root = tk.Tk()
            root.withdraw()
            messagebox.showwarning(
                "Backend unavailable",
                "Backend could not be started automatically.\n"
                "The simulator will continue in cache/local mode if files are available."
            )
            root.destroy()
    else:
        logger.info("Backend already running.")

    from app import FootballSimulator

    root = tk.Tk()
    app = FootballSimulator(root)
    root.mainloop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())