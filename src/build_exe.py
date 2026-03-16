from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent
DIST = ROOT / "dist"
BUILD = ROOT / "build"


def main() -> int:
    entry = ROOT / "run_simulator.py"
    if not entry.exists():
        print("run_simulator.py not found")
        return 1

    cmd = [
        sys.executable,
        "-m",
        "PyInstaller",
        "--noconfirm",
        "--clean",
        "--windowed",
        "--name",
        "JuggerNei8Simulator",
        str(entry),
    ]

    result = subprocess.run(cmd, cwd=str(ROOT))
    if result.returncode != 0:
        return result.returncode

    print("EXE build complete.")
    print(DIST / "JuggerNei8Simulator")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())