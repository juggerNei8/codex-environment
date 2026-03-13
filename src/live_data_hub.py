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

        # your richer second source / custom backend
        self.secondary_player_api = os.getenv("SECONDARY_PLAYER_API_URL", "").strip()
        self.secondary_player_api_key = os.getenv("SECONDARY_PLAYER_API_KEY", "").strip()

    # ------------------------------------------------

    def refresh_all(self, database_dir, competition_code="PL"):
        os.makedirs(database_dir, exist_ok=True)

        result = {"updated": False, "notes": []}

        if not REQUESTS_AVAILABLE:
            result["notes"].append("requests not installed")
            return result

        if self.football_api_key:
            try:
                self.refresh_teams(database_dir, competition_code)
                self.refresh_fixtures(database_dir, competition_code)
                self.refresh_league_table(database_dir, competition_code)
                self.refresh_team_form(database_dir)
                result["updated"] = True
                result["notes"].append("football-data refreshed")
            except Exception as e:
                result["notes"].append(f"football-data failed: {e}")
        else:
            result["notes"].append("FOOTBALL_DATA_API_KEY not set")

        try:
            self.ensure_players_exists(database_dir)
            self.refresh_players_from_secondary(database_dir)
        except Exception as e:
            result["notes"].append(f"secondary players skipped: {e}")

        return result

    # ------------------------------------------------

    def football_headers(self):
        return {"X-Auth-Token": self.football_api_key}

    def secondary_headers(self):
        headers = {}
        if self.secondary_player_api_key:
            headers["Authorization"] = f"Bearer {self.secondary_player_api_key}"
        return headers

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
                "shortName": team.get("shortName", "")
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

    def refresh_team_form(self, database_dir):
        teams_path = os.path.join(database_dir, "teams.csv")
        if not os.path.exists(teams_path):
            return

        import pandas as pd
        teams_df = pd.read_csv(teams_path)

        if "team" not in teams_df.columns:
            return

        rows = []
        for team_name in teams_df["team"].dropna().astype(str).tolist():
            rows.append({
                "team": team_name,
                "form_last5": 0.60,
                "injuries_count": 0,
                "cards_pressure": 0.14,
                "morale": 0.66
            })

        self.write_csv(os.path.join(database_dir, "team_form.csv"), rows)

    # ------------------------------------------------

    def ensure_players_exists(self, database_dir):
        path = os.path.join(database_dir, "players.csv")
        if os.path.exists(path) and os.path.getsize(path) > 0:
            return

        rows = [
            {"player": "Bukayo Saka", "team": "Arsenal", "position": "RW", "rating": 87, "number": 7},
            {"player": "Martin Odegaard", "team": "Arsenal", "position": "CAM", "rating": 88, "number": 8},
            {"player": "Cole Palmer", "team": "Chelsea", "position": "CAM", "rating": 86, "number": 20},
            {"player": "Jude Bellingham", "team": "Real Madrid", "position": "CM", "rating": 90, "number": 5},
        ]
        self.write_csv(path, rows)

    # ------------------------------------------------
    # YOUR SECONDARY PLAYER / CLUB API
    # ------------------------------------------------

    def refresh_players_from_secondary(self, database_dir):
        if not self.secondary_player_api or not REQUESTS_AVAILABLE:
            return

        r = requests.get(self.secondary_player_api, headers=self.secondary_headers(), timeout=25)
        r.raise_for_status()
        data = r.json()

        players = data.get("players", [])
        if players:
            rows = []
            for p in players:
                rows.append({
                    "player": p.get("name", ""),
                    "team": p.get("team", ""),
                    "position": p.get("position", ""),
                    "rating": p.get("rating", 75),
                    "number": p.get("number", ""),
                    "nationality": p.get("nationality", ""),
                    "value": p.get("value", 10),
                    "clause": p.get("clause", ""),
                    "agent": p.get("agent", ""),
                    "stats": p.get("stats", ""),
                    "proficiency": p.get("proficiency", ""),
                    "association": p.get("association", ""),
                    "attachment": p.get("attachment", ""),
                    "objectives": p.get("objectives", ""),
                    "injury_risk": p.get("injury_risk", 0.08),
                    "form": p.get("form", 0.60),
                })
            self.write_csv(os.path.join(database_dir, "players.csv"), rows)

    # ------------------------------------------------

    def write_csv(self, path, rows):
        if not rows:
            return

        fieldnames = list(rows[0].keys())
        with open(path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows)