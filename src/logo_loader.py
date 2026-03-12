import os
from tkinter import PhotoImage


class LogoLoader:

    def __init__(self):

        self.cache = {}

        self.base_path = os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            "..",
            "assets",
            "logos"
        )

    # --------------------------------

    def load(self, team):

        if team in self.cache:
            return self.cache[team]

        filename = team.replace(" ", "_") + ".png"

        path = os.path.join(self.base_path, filename)

        if os.path.exists(path):

            logo = PhotoImage(file=path)

            self.cache[team] = logo

            return logo

        return None