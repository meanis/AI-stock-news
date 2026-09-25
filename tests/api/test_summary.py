from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient

from app.api.dependencies import get_summary_service
from app.domain.models import Article, StockSummary, Takeaway
from app.main import app


def _article() -> Article:
    return Article(
        id="a1",
        headline="Acme beats earnings",
        summary="Acme reported Q3 results above expectations.",
        source="Reuters",
        url="https://example.com/a1",
        published_at=datetime(2024, 9, 10, tzinfo=timezone.utc),
    )


class _StubSummaryService:
    def __init__(self, response: StockSummary | None = None, error: Exception | None = None):
        self._response = response
        self._error = error

    async def get_summary(self, ticker: str) -> StockSummary:
        if self._error is not None:
            raise self._error
        return self._response


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
    monkeypatch.setenv("FINNHUB_API_KEY", "finnhub-test")
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


def test_get_summary_happy_path(client):
    response = StockSummary(
        ticker="ACME",
        overall_sentiment="positive",
        takeaways=[Takeaway(text="Strong quarter", article_ids=["a1"])],
        risk_note="Guidance was not raised.",
        articles=[_article()],
        source_provider="finnhub",
        summary_status="ok",
    )
    app.dependency_overrides[get_summary_service] = lambda: _StubSummaryService(response=response)

    result = client.get("/api/summary/ACME")

    assert result.status_code == 200
    body = result.json()
    assert body["ticker"] == "ACME"
    assert body["summary_status"] == "ok"
    assert body["source_provider"] == "finnhub"
    assert body["takeaways"][0]["article_ids"] == ["a1"]


def test_get_summary_no_news_found(client):
    response = StockSummary(
        ticker="UNKNOWNTICKER",
        overall_sentiment="neutral",
        takeaways=[],
        risk_note="No recent news found for UNKNOWNTICKER.",
        articles=[],
        source_provider="finnhub",
        summary_status="ok",
    )
    app.dependency_overrides[get_summary_service] = lambda: _StubSummaryService(response=response)

    result = client.get("/api/summary/UNKNOWNTICKER")

    assert result.status_code == 200
    body = result.json()
    assert body["articles"] == []
    assert body["summary_status"] == "ok"


def test_get_summary_surfaces_degraded_flag(client):
    response = StockSummary(
        ticker="ACME",
        overall_sentiment="unknown",
        takeaways=[],
        risk_note="Summary unavailable; showing headlines only.",
        articles=[_article()],
        source_provider="finnhub",
        summary_status="degraded",
    )
    app.dependency_overrides[get_summary_service] = lambda: _StubSummaryService(response=response)

    result = client.get("/api/summary/ACME")

    assert result.status_code == 200
    assert result.json()["summary_status"] == "degraded"


def test_get_summary_returns_503_on_provider_outage(client):
    app.dependency_overrides[get_summary_service] = lambda: _StubSummaryService(
        error=RuntimeError("both providers down")
    )

    result = client.get("/api/summary/ACME")

    assert result.status_code == 503
