import os
import csv
import json

try:
    import requests
    REQUESTS_AVAILABLE = True
except Exception:
    REQUESTS_AVAILABLE = False


class LiveDataHub:
    def __init__(self):
        self.football_data_key = os.getenv("FOOTBALL_DATA_API_KEY", "").strip()
        self.news_api_key = os.getenv("NEWSAPI_KEY", "").strip()

    def refresh_all(self, database_dir):
        os.makedirs(database_dir, exist_ok=True)

        updated = False
        notes = []

        if REQUESTS_AVAILABLE and self.football_data_key:
            try:
                self.refresh_teams(database_dir)
                self.refresh_fixtures(database_dir)
                self.refresh_standings(database_dir)
                updated = True
                notes.append("football-data updated")
            except Exception as e:
                notes.append(f"football-data failed: {e}")
        else:
            notes.append("football-data skipped")

        if REQUESTS_AVAILABLE and self.news_api_key:
            try:
                self.refresh_news(database_dir)
                updated = True
                notes.append("news updated")
            except Exception as e:
                notes.append(f"news failed: {e}")
        else:
            notes.append("news skipped")

        return {"updated": updated, "notes": notes}

    def headers(self):
        return {"X-Auth-Token": self.football_data_key}

    def refresh_teams(self, database_dir):
        # Example competition: Premier League = PL
        url = "https://api.football-data.org/v4/competitions/PL/teams"
        r = requests.get(url, headers=self.headers(), timeout=20)
        r.raise_for_status()
        data = r.json()

        rows = []
        for t in data.get("teams", []):
            rows.append({
                "team": t.get("name", ""),
                "league": "Premier League",
                "country": (t.get("area") or {}).get("name", ""),
                "strength": 80
            })

        if rows:
            self.write_csv(os.path.join(database_dir, "teams.csv"), rows)

    def refresh_fixtures(self, database_dir):
        url = "https://api.football-data.org/v4/competitions/PL/matches"
        r = requests.get(url, headers=self.headers(), timeout=20)
        r.raise_for_status()
        data = r.json()

        rows = []
        for m in data.get("matches", [])[:100]:
            rows.append({
                "home": ((m.get("homeTeam") or {}).get("name", "")),
                "away": ((m.get("awayTeam") or {}).get("name", "")),
                "competition": ((m.get("competition") or {}).get("name", "")),
                "utcDate": m.get("utcDate", ""),
                "status": m.get("status", "")
            })

        if rows:
            self.write_csv(os.path.join(database_dir, "fixtures.csv"), rows)

    def refresh_standings(self, database_dir):
        url = "https://api.football-data.org/v4/competitions/PL/standings"
        r = requests.get(url, headers=self.headers(), timeout=20)
        r.raise_for_status()
        data = r.json()

        rows = []
        standings = data.get("standings", [])
        if standings:
            table = standings[0].get("table", [])
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

        if rows:
            self.write_csv(os.path.join(database_dir, "league_table.csv"), rows)

    def refresh_news(self, database_dir):
        url = "https://newsapi.org/v2/everything"
        params = {
            "q": "football OR soccer transfer injury match",
            "language": "en",
            "sortBy": "publishedAt",
            "pageSize": 20,
            "apiKey": self.news_api_key
        }
        r = requests.get(url, params=params, timeout=20)
        r.raise_for_status()
        data = r.json()

        rows = []
        for art in data.get("articles", []):
            title = art.get("title", "")
            desc = art.get("description", "") or ""
            rows.append({
                "team": "General",
                "title": title,
                "summary": desc[:220]
            })

        if rows:
            self.write_csv(os.path.join(database_dir, "club_news.csv"), rows)

    def write_csv(self, path, rows):
        if not rows:
            return

        fieldnames = list(rows[0].keys())
        with open(path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows)