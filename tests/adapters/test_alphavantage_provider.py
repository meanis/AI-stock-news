import json
from pathlib import Path

import httpx
import pytest
import respx

from app.adapters.news.alphavantage import AlphaVantageNewsProvider

FIXTURE = Path(__file__).parent.parent / "fixtures" / "alphavantage_news_sentiment.json"
BASE_URL = "https://www.alphavantage.co/query"


def _provider() -> AlphaVantageNewsProvider:
    return AlphaVantageNewsProvider(api_key="test-key", lookback_days=7, base_url=BASE_URL)


@pytest.mark.asyncio
@respx.mock
async def test_fetch_sends_tickers_apikey_and_time_from_params():
    route = respx.get(BASE_URL).mock(return_value=httpx.Response(200, json={"feed": []}))

    await _provider().fetch("ACME")

    assert route.called
    request = route.calls.last.request
    params = dict(httpx.QueryParams(request.url.query))
    assert params["function"] == "NEWS_SENTIMENT"
    assert params["tickers"] == "ACME"
    assert params["apikey"] == "test-key"
    assert "time_from" in params


@pytest.mark.asyncio
@respx.mock
async def test_fetch_maps_feed_into_articles():
    raw = json.loads(FIXTURE.read_text())
    respx.get(BASE_URL).mock(return_value=httpx.Response(200, json=raw))

    result = await _provider().fetch("ACME")
    articles = result.articles

    assert len(articles) == 2
    assert result.source_provider == "alphavantage"


@pytest.mark.asyncio
@respx.mock
async def test_fetch_returns_empty_list_when_feed_key_missing():
    respx.get(BASE_URL).mock(
        return_value=httpx.Response(200, json={"Information": "rate limit reached"})
    )

    result = await _provider().fetch("ACME")
    articles = result.articles

    assert articles == []


@pytest.mark.asyncio
@respx.mock
async def test_fetch_raises_on_non_200_response():
    respx.get(BASE_URL).mock(return_value=httpx.Response(500, json={"error": "boom"}))

    with pytest.raises(httpx.HTTPStatusError):
        await _provider().fetch("ACME")


@pytest.mark.asyncio
@respx.mock
async def test_fetch_raises_on_timeout():
    respx.get(BASE_URL).mock(side_effect=httpx.TimeoutException("timed out"))

    with pytest.raises(httpx.TimeoutException):
        await _provider().fetch("ACME")
