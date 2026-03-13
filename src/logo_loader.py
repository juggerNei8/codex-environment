import os
import tkinter as tk


class LogoLoader:
    def __init__(self):
        self.cache = {}

    def base_dir(self):
        here = os.path.dirname(os.path.abspath(__file__))
        return os.path.normpath(os.path.join(here, "..", "assets", "logos"))

    def safe_name(self, name):
        return (
            name.lower()
            .replace(" ", "_")
            .replace("/", "_")
            .replace("\\", "_")
            .replace("-", "_")
        )

    def find_logo_path(self, team_name):
        base = self.base_dir()
        if not os.path.exists(base):
            return None

        filename = self.safe_name(team_name) + ".png"
        path = os.path.join(base, filename)
        if os.path.exists(path):
            return path

        return None

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