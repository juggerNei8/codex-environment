from __future__ import annotations

import threading
from typing import Callable, Any


def run_in_background(
    fn: Callable[[], Any],
    on_done: Callable[[Any], None],
    on_error: Callable[[Exception], None] | None = None,
) -> None:
    """
    Tkinter-friendly helper:
    - runs work off the UI thread
    - returns result via callback
    """
    def _worker():
        try:
            result = fn()
            on_done(result)
        except Exception as e:
            if on_error:
                on_error(e)
            else:
                on_done(None)

    threading.Thread(target=_worker, daemon=True).start()