import os
import pandas as pd
import random


class TransferMarket:
    def __init__(self):
        self.market = pd.DataFrame()

    # ------------------------------------------------

    def build_from_players(self, players_df):
        if players_df is None or players_df.empty:
            self.market = pd.DataFrame(columns=["player", "team", "position", "value", "rating"])
            return self.market

        candidates = players_df.sample(min(80, len(players_df)), random_state=7).copy()
        if "value" not in candidates.columns:
            candidates["value"] = 10

        self.market = candidates[["player", "team", "position", "value", "rating"]].reset_index(drop=True)
        return self.market

    # ------------------------------------------------

    def save_to_csv(self, database_dir):
        os.makedirs(database_dir, exist_ok=True)
        path = os.path.join(database_dir, "transfer_market.csv")
        self.market.to_csv(path, index=False)

    # ------------------------------------------------

    def load_from_csv(self, database_dir):
        path = os.path.join(database_dir, "transfer_market.csv")
        if os.path.exists(path) and os.path.getsize(path) > 0:
            try:
                self.market = pd.read_csv(path)
            except Exception:
                self.market = pd.DataFrame()
        else:
            self.market = pd.DataFrame()
        return self.market