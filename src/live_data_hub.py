import os
import csv
from datetime import datetime, timedelta

try:
    import requests
    REQUESTS_AVAILABLE = True
except Exception:
    REQUESTS_AVAILABLE = False


class LiveDataHub:
    def __init__(self):
        self.football_api_key = os.getenv("FOOTBALL_DATA_API_KEY", "").strip()
        self.news_api_key = os.getenv("NEWSAPI_KEY", "").strip()

    # ------------------------------------------------

    def refresh_all(self, database_dir, competition_code="PL"):
        os.makedirs(database_dir, exist_ok=True)

        result = {"updated": False, "notes": []}

        if not REQUESTS_AVAILABLE:
            result["notes"].append("requests not installed")
            return result

        if not self.football_api_key:
            result["notes"].append("FOOTBALL_DATA_API_KEY not set")
            return result

        try:
            self.refresh_teams(database_dir, competition_code)
            self.refresh_fixtures(database_dir, competition_code)
            self.refresh_league_table(database_dir, competition_code)
            self.refresh_team_form(database_dir, competition_code)
            result["updated"] = True
            result["notes"].append("teams, fixtures, standings, form updated")
        except Exception as e:
            result["notes"].append(f"football update failed: {e}")

        return result

    # ------------------------------------------------

    def football_headers(self):
        return {"X-Auth-Token": self.football_api_key}

    # ------------------------------------------------

    def refresh_teams(self, database_dir, competition_code):
        url = f"https://api.football-data.org/v4/competitions/{competition_code}/teams"
        r = requests.get(url, headers=self.football_headers(), timeout=25)
        r.raise_for_status()
        data = r.json()

        rows = []
        for team in data.get("teams", []):
            rows.append({
                "team": team.get("name", ""),
                "league": (data.get("competition") or {}).get("name", ""),
                "country": (team.get("area") or {}).get("name", ""),
                "strength": 80,
                "stadium": team.get("venue", ""),
                "founded": team.get("founded", ""),
                "shortName": team.get("shortName", ""),
            })

        self.write_csv(os.path.join(database_dir, "teams.csv"), rows)

    # ------------------------------------------------

    def refresh_fixtures(self, database_dir, competition_code):
        date_from = datetime.utcnow().date().isoformat()
        date_to = (datetime.utcnow().date() + timedelta(days=21)).isoformat()

        url = (
            f"https://api.football-data.org/v4/competitions/{competition_code}/matches"
            f"?dateFrom={date_from}&dateTo={date_to}"
        )
        r = requests.get(url, headers=self.football_headers(), timeout=25)
        r.raise_for_status()
        data = r.json()

        rows = []
        for match in data.get("matches", []):
            rows.append({
                "home": ((match.get("homeTeam") or {}).get("name", "")),
                "away": ((match.get("awayTeam") or {}).get("name", "")),
                "competition": ((match.get("competition") or {}).get("name", "")),
                "utcDate": match.get("utcDate", ""),
                "status": match.get("status", "")
            })

        self.write_csv(os.path.join(database_dir, "fixtures.csv"), rows)

    # ------------------------------------------------

    def refresh_league_table(self, database_dir, competition_code):
        url = f"https://api.football-data.org/v4/competitions/{competition_code}/standings"
        r = requests.get(url, headers=self.football_headers(), timeout=25)
        r.raise_for_status()
        data = r.json()

        standings = data.get("standings", [])
        table = standings[0].get("table", []) if standings else []

        rows = []
        for row in table:
            team = row.get("team", {})
            rows.append({
                "team": team.get("name", ""),
                "played": row.get("playedGames", 0),
                "wins": row.get("won", 0),
                "draws": row.get("draw", 0),
                "losses": row.get("lost", 0),
                "gd": row.get("goalDifference", 0),
                "points": row.get("points", 0)
            })

        self.write_csv(os.path.join(database_dir, "league_table.csv"), rows)

    # ------------------------------------------------
    # RECENT FORM / HISTORY
    # ------------------------------------------------

    def refresh_team_form(self, database_dir, competition_code):
        teams_path = os.path.join(database_dir, "teams.csv")
        if not os.path.exists(teams_path):
            return

        import pandas as pd
        teams_df = pd.read_csv(teams_path)
        if "team" not in teams_df.columns:
            return

        # lightweight form table for predictions
        rows = []
        for team_name in teams_df["team"].dropna().astype(str).tolist()[:30]:
            rows.append({
                "team": team_name,
                "form_last5": round(0.55, 2),
                "injuries_count": 0,
                "cards_pressure": 0.15,
                "morale": 0.65
            })

        self.write_csv(os.path.join(database_dir, "team_form.csv"), rows)

    # ------------------------------------------------

    def ensure_players_exists(self, database_dir):
        path = os.path.join(database_dir, "players.csv")
        if os.path.exists(path) and os.path.getsize(path) > 0:
            return

        rows = [
            {"player": "Bukayo Saka", "team": "Arsenal", "position": "RW", "rating": 87},
            {"player": "Martin Odegaard", "team": "Arsenal", "position": "CAM", "rating": 88},
            {"player": "Cole Palmer", "team": "Chelsea", "position": "CAM", "rating": 86},
            {"player": "Jude Bellingham", "team": "Real Madrid", "position": "CM", "rating": 90},
        ]
        self.write_csv(path, rows)

    # ------------------------------------------------

    def write_csv(self, path, rows):
        if not rows:
            return

        fieldnames = list(rows[0].keys())
        with open(path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows)