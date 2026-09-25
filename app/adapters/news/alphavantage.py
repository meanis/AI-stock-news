from datetime import datetime, timedelta, timezone

import httpx

from app.adapters import http_client
from app.adapters.news.mapper import map_alphavantage_articles
from app.domain.models import NewsResult


class AlphaVantageNewsProvider:
    def __init__(
        self,
        api_key: str,
        lookback_days: int,
        base_url: str = "https://www.alphavantage.co/query",
        http_client: httpx.AsyncClient | None = None,
    ) -> None:
        self._api_key = api_key
        self._lookback_days = lookback_days
        self._base_url = base_url
        self._http_client = http_client

    async def fetch(self, ticker: str) -> NewsResult:
        time_from = datetime.now(timezone.utc) - timedelta(days=self._lookback_days)
        params = {
            "function": "NEWS_SENTIMENT",
            "tickers": ticker,
            "time_from": time_from.strftime("%Y%m%dT%H%M"),
            "apikey": self._api_key,
        }

        response = await http_client.get(self._http_client, self._base_url, params)
        return NewsResult(
            articles=map_alphavantage_articles(response.json().get("feed", [])),
            source_provider="alphavantage",
        )
