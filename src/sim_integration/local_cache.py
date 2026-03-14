from __future__ import annotations

import json
import os
import time
from typing import Any, Optional


def file_exists(path: str) -> bool:
    return os.path.exists(path) and os.path.isfile(path)


def file_age_seconds(path: str) -> Optional[int]:
    if not file_exists(path):
        return None
    try:
        return int(time.time() - os.path.getmtime(path))
    except OSError:
        return None


def read_json(path: str) -> Optional[Any]:
    if not file_exists(path):
        return None
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None


def is_fresh(path: str, max_age_seconds: int) -> bool:
    age = file_age_seconds(path)
    if age is None:
        return False
    return age <= max_age_seconds