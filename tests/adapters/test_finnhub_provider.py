import json
from pathlib import Path

import httpx
import pytest
import respx

from app.adapters.news.finnhub import FinnhubNewsProvider

FIXTURE = Path(__file__).parent.parent / "fixtures" / "finnhub_company_news.json"
BASE_URL = "https://finnhub.io/api/v1"


def _provider() -> FinnhubNewsProvider:
    return FinnhubNewsProvider(api_key="test-key", lookback_days=7, base_url=BASE_URL)


@pytest.mark.asyncio
@respx.mock
async def test_fetch_sends_symbol_from_to_and_token_params():
    route = respx.get(f"{BASE_URL}/company-news").mock(
        return_value=httpx.Response(200, json=[])
    )

    await _provider().fetch("ACME")

    assert route.called
    request = route.calls.last.request
    params = dict(httpx.QueryParams(request.url.query))
    assert params["symbol"] == "ACME"
    assert params["token"] == "test-key"
    assert "from" in params and "to" in params


@pytest.mark.asyncio
@respx.mock
async def test_fetch_maps_response_into_articles():
    raw = json.loads(FIXTURE.read_text())
    respx.get(f"{BASE_URL}/company-news").mock(return_value=httpx.Response(200, json=raw))

    result = await _provider().fetch("ACME")
    articles = result.articles

    assert len(articles) == 2
    assert result.source_provider == "finnhub"
    assert {a.id for a in articles} == {"111000111", "111000112"}


@pytest.mark.asyncio
@respx.mock
async def test_fetch_returns_empty_list_when_no_articles():
    respx.get(f"{BASE_URL}/company-news").mock(return_value=httpx.Response(200, json=[]))

    result = await _provider().fetch("ACME")
    articles = result.articles

    assert articles == []


@pytest.mark.asyncio
@respx.mock
async def test_fetch_raises_on_non_200_response():
    respx.get(f"{BASE_URL}/company-news").mock(
        return_value=httpx.Response(500, json={"error": "boom"})
    )

    with pytest.raises(httpx.HTTPStatusError):
        await _provider().fetch("ACME")


@pytest.mark.asyncio
@respx.mock
async def test_fetch_raises_on_timeout():
    respx.get(f"{BASE_URL}/company-news").mock(side_effect=httpx.TimeoutException("timed out"))

    with pytest.raises(httpx.TimeoutException):
        await _provider().fetch("ACME")
