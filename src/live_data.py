import requests

def get_live_score(team1, team2):
    """
    Placeholder for live API scores. Replace with a real API key.
    """
    # Example API URL
    # response = requests.get(f"https://api.sportsdata.io/soccer?team1={team1}&team2={team2}&key=YOUR_KEY")
    # return response.json()
    return {"team1": team1, "team2": team2, "score": "2-1"}
import requests

url = "https://api.football-data.org/v4/matches"
headers = {"X-Auth-Token": "YOUR_API_KEY"}

response = requests.get(url, headers=headers)

print(response.json())