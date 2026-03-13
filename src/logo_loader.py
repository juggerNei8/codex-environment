import os
import tkinter as tk


class LogoLoader:
    def __init__(self):
        self.cache = {}

    # ------------------------------------------------

    def base_dir(self):
        here = os.path.dirname(os.path.abspath(__file__))
        return os.path.normpath(os.path.join(here, "..", "assets", "logos"))

    # ------------------------------------------------

    def find_logo_path(self, team_name):
        base = self.base_dir()
        if not os.path.exists(base):
            return None

        normalized = team_name.lower().replace(" ", "").replace("-", "")

        for root, _, files in os.walk(base):
            for f in files:
                low = f.lower().replace(" ", "").replace("-", "")
                if normalized in low and (f.lower().endswith(".png") or f.lower().endswith(".gif")):
                    return os.path.join(root, f)

        return None

    # ------------------------------------------------

    def load(self, team_name):
        if team_name in self.cache:
            return self.cache[team_name]

        path = self.find_logo_path(team_name)
        if not path:
            return None

        try:
            img = tk.PhotoImage(file=path)
            self.cache[team_name] = img
            return img
        except Exception:
            return None