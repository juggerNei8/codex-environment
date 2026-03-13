import os
import csv
from datetime import datetime, timedelta

try:
    import requests
    REQUESTS_AVAILABLE = True
except Exception:
    REQUESTS_AVAILABLE = False


class LiveDataHub:
    """
    Refreshes local CSV files from live APIs.
    Safe behavior:
    - if requests is missing, no crash
    - if API keys are missing, no crash
    - if internet fails, no crash
    """

    def __init__(self):
        self.football_api_key = os.getenv("FOOTBALL_DATA_API_KEY", "").strip()
        self.news_api_key = os.getenv("NEWSAPI_KEY", "").strip()

    # ------------------------------------------------

    def refresh_all(self, database_dir, competition_code="PL"):
        os.makedirs(database_dir, exist_ok=True)

        result = {
            "updated": False,
            "notes": []
        }

        if not REQUESTS_AVAILABLE:
            result["notes"].append("requests not installed")
            return result

        if not self.football_api_key:
            result["notes"].append("FOOTBALL_DATA_API_KEY not set")
        else:
            try:
                self.refresh_teams(database_dir, competition_code)
                self.refresh_fixtures(database_dir, competition_code)
                self.refresh_league_table(database_dir, competition_code)
                result["updated"] = True
                result["notes"].append("football data updated")
            except Exception as e:
                result["notes"].append(f"football update failed: {e}")

        if self.news_api_key:
            try:
                self.refresh_club_news(database_dir)
                result["updated"] = True
                result["notes"].append("club news updated")
            except Exception as e:
                result["notes"].append(f"news update failed: {e}")
        else:
            result["notes"].append("NEWSAPI_KEY not set")

        return result

    # ------------------------------------------------

    def football_headers(self):
        return {"X-Auth-Token": self.football_api_key}

    # ------------------------------------------------
    # TEAMS
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
                "founded": team.get("founded", ""),
                "stadium": team.get("venue", ""),
                "shortName": team.get("shortName", "")
            })

        self.write_csv(os.path.join(database_dir, "teams.csv"), rows)

    # ------------------------------------------------
    # FIXTURES
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
    # LEAGUE TABLE
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
    # CLUB NEWS
    # ------------------------------------------------

    def refresh_club_news(self, database_dir):
        url = "https://newsapi.org/v2/everything"
        params = {
            "q": "football OR soccer injuries transfers standings match preview",
            "language": "en",
            "sortBy": "publishedAt",
            "pageSize": 20,
            "apiKey": self.news_api_key
        }

        r = requests.get(url, params=params, timeout=25)
        r.raise_for_status()
        data = r.json()

        rows = []
        for article in data.get("articles", []):
            rows.append({
                "team": "General",
                "title": article.get("title", ""),
                "summary": (article.get("description") or "")[:220]
            })

        self.write_csv(os.path.join(database_dir, "club_news.csv"), rows)

    # ------------------------------------------------
    # PLAYERS
    # ------------------------------------------------

    def ensure_players_exists(self, database_dir):
        """
        football-data public docs are great for teams/matches/standings.
        For players, keep a local CSV unless you add a separate source.
        This prevents crashes.
        """
        path = os.path.join(database_dir, "players.csv")
        if os.path.exists(path):
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