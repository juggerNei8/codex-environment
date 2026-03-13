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
        self.thesportsdb_api_key = os.getenv("THESPORTSDB_API_KEY", "123")  # demo / free-style default

    # ------------------------------------------------

    def refresh_all(self, database_dir, assets_dir, competition_code="PL"):
        os.makedirs(database_dir, exist_ok=True)
        os.makedirs(os.path.join(assets_dir, "logos"), exist_ok=True)

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
        except Exception as e:
            result["notes"].append(f"players seed failed: {e}")

        try:
            self.refresh_logos(database_dir, assets_dir)
            result["notes"].append("logos refreshed")
        except Exception as e:
            result["notes"].append(f"logos refresh failed: {e}")

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
                "website": team.get("website", "")
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
    # THESPORTSDB LOGOS
    # ------------------------------------------------

    def refresh_logos(self, database_dir, assets_dir):
        teams_path = os.path.join(database_dir, "teams.csv")
        if not os.path.exists(teams_path):
            return

        import pandas as pd
        teams_df = pd.read_csv(teams_path)
        if "team" not in teams_df.columns:
            return

        logos_dir = os.path.join(assets_dir, "logos")
        os.makedirs(logos_dir, exist_ok=True)

        for team_name in teams_df["team"].dropna().astype(str).tolist()[:40]:
            filename = self.safe_name(team_name) + ".png"
            target = os.path.join(logos_dir, filename)

            if os.path.exists(target) and os.path.getsize(target) > 0:
                continue

            url = f"https://www.thesportsdb.com/api/v1/json/{self.thesportsdb_api_key}/searchteams.php"
            r = requests.get(url, params={"t": team_name}, timeout=20)
            r.raise_for_status()
            data = r.json()

            teams = data.get("teams")
            if not teams:
                continue

            badge_url = teams[0].get("strBadge")
            if not badge_url:
                continue

            img = requests.get(badge_url, timeout=20)
            img.raise_for_status()

            with open(target, "wb") as f:
                f.write(img.content)

    # ------------------------------------------------

    def safe_name(self, name):
        return (
            name.lower()
            .replace(" ", "_")
            .replace("/", "_")
            .replace("\\", "_")
            .replace("-", "_")
        )

    def write_csv(self, path, rows):
        if not rows:
            return

        fieldnames = list(rows[0].keys())
        with open(path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows)