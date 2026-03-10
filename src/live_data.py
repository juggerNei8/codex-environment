import requests

def get_live_scores():

    try:
        url="https://api.football-data.org/v4/matches"
        r=requests.get(url)

        if r.status_code==200:
            return "Live data retrieved"
        else:
            return "Live API unavailable"

    except:
        return "Internet connection failed"