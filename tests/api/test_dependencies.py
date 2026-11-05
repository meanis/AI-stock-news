import json
from pathlib import Path

import httpx
import pytest
import respx

from app.api.dependencies import get_summary_service

FIXTURES = Path(__file__).parent.parent / "fixtures"


def _mock_upstreams() -> respx.Route:
    news = json.loads((FIXTURES / "finnhub_company_news.json").read_text())
    respx.get("https://finnhub.io/api/v1/company-news").mock(
        return_value=httpx.Response(200, json=news)
    )
    completion = json.loads((FIXTURES / "openai_chat_completion.json").read_text())
    completion["choices"][0]["message"]["content"] = json.dumps(
        {
            "overall_sentiment": "positive",
            "takeaways": [{"text": "Strong quarter", "article_ids": ["111000111"]}],
            "risk_note": "None noted.",
        }
    )
    return respx.post("https://api.openai.com/v1/chat/completions").mock(
        return_value=httpx.Response(200, json=completion)
    )


@pytest.mark.asyncio
@respx.mock
async def test_summary_service_caches_llm_summaries(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
    monkeypatch.setenv("FINNHUB_API_KEY", "finnhub-test")
    monkeypatch.delenv("ALPHAVANTAGE_API_KEY", raising=False)
    monkeypatch.delenv("SUMMARY_CACHE_TTL_SECONDS", raising=False)
    openai_route = _mock_upstreams()
    service = get_summary_service()

    first = await service.get_summary("ACME")
    second = await service.get_summary("ACME")

    assert openai_route.call_count == 1
    assert second == first


@pytest.mark.asyncio
@respx.mock
async def test_summary_cache_can_be_disabled_via_settings(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
    monkeypatch.setenv("FINNHUB_API_KEY", "finnhub-test")
    monkeypatch.delenv("ALPHAVANTAGE_API_KEY", raising=False)
    monkeypatch.setenv("SUMMARY_CACHE_TTL_SECONDS", "0")
    openai_route = _mock_upstreams()
    service = get_summary_service()

    await service.get_summary("ACME")
    await service.get_summary("ACME")

    assert openai_route.call_count == 2
