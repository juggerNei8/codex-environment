import os
import re
from dataclasses import dataclass

try:
    import requests
    REQUESTS_AVAILABLE = True
except Exception:
    REQUESTS_AVAILABLE = False


@dataclass
class ArticleSignal:
    team: str
    article_count: int
    morale_delta: float
    injury_risk_delta: float
    transfer_noise: float
    sentiment_score: float
    summary: str


class ArticleIngestion:
    """
    Pulls article data and converts it into simple NLP-like features.
    This is intentionally dependency-light and uses keyword inference
    so it can run without heavyweight NLP packages.
    """

    POSITIVE_WORDS = {
        "win", "won", "victory", "dominant", "excellent", "sharp", "boost",
        "fit", "return", "comeback", "confidence", "impressive", "strong"
    }

    NEGATIVE_WORDS = {
        "injury", "doubt", "loss", "suspended", "ban", "fatigue", "poor",
        "crisis", "pressure", "weak", "setback", "out", "hamstring", "ankle"
    }

    TRANSFER_WORDS = {
        "transfer", "bid", "linked", "target", "move", "deal", "contract"
    }

    def __init__(self):
        self.news_api_key = os.getenv("NEWSAPI_KEY", "").strip()

    def fetch_articles(self, query: str, page_size: int = 20) -> list[dict]:
        if not REQUESTS_AVAILABLE or not self.news_api_key:
            return []

        url = "https://newsapi.org/v2/everything"
        params = {
            "q": query,
            "language": "en",
            "sortBy": "publishedAt",
            "pageSize": page_size,
            "apiKey": self.news_api_key,
        }

        r = requests.get(url, params=params, timeout=20)
        r.raise_for_status()
        data = r.json()

        return data.get("articles", [])

    def score_text(self, text: str) -> tuple[float, float, float, float]:
        tokens = re.findall(r"[A-Za-z']+", (text or "").lower())

        pos = sum(1 for t in tokens if t in self.POSITIVE_WORDS)
        neg = sum(1 for t in tokens if t in self.NEGATIVE_WORDS)
        transfer = sum(1 for t in tokens if t in self.TRANSFER_WORDS)

        sentiment = (pos - neg) / max(1, len(tokens) ** 0.5)
        morale_delta = max(-0.20, min(0.20, sentiment * 0.12))
        injury_delta = min(0.25, neg * 0.015)
        transfer_noise = min(0.30, transfer * 0.02)

        return sentiment, morale_delta, injury_delta, transfer_noise

    def build_signal_for_team(self, team: str) -> ArticleSignal:
        articles = self.fetch_articles(team)
        combined = " ".join(
            ((a.get("title") or "") + " " + (a.get("description") or ""))
            for a in articles
        )

        sentiment, morale_delta, injury_delta, transfer_noise = self.score_text(combined)

        summary = (
            f"{team}: articles={len(articles)}, "
            f"sentiment={sentiment:.3f}, morale_delta={morale_delta:.3f}, "
            f"injury_delta={injury_delta:.3f}, transfer_noise={transfer_noise:.3f}"
        )

        return ArticleSignal(
            team=team,
            article_count=len(articles),
            morale_delta=morale_delta,
            injury_risk_delta=injury_delta,
            transfer_noise=transfer_noise,
            sentiment_score=sentiment,
            summary=summary,
        )