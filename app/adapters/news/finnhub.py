from datetime import date, timedelta

import httpx

from app.adapters import http_client
from app.adapters.news.mapper import map_finnhub_articles
from app.domain.models import NewsResult


class FinnhubNewsProvider:
    def __init__(
        self,
        api_key: str,
        lookback_days: int,
        base_url: str = "https://finnhub.io/api/v1",
        http_client: httpx.AsyncClient | None = None,
    ) -> None:
        self._api_key = api_key
        self._lookback_days = lookback_days
        self._base_url = base_url
        self._http_client = http_client

    async def fetch(self, ticker: str) -> NewsResult:
        today = date.today()
        params = {
            "symbol": ticker,
            "from": (today - timedelta(days=self._lookback_days)).isoformat(),
            "to": today.isoformat(),
            "token": self._api_key,
        }

        response = await http_client.get(
            self._http_client, f"{self._base_url}/company-news", params
        )
        return NewsResult(
            articles=map_finnhub_articles(response.json()), source_provider="finnhub"
        )
