from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from app.domain.models import Article, StockSummary, Takeaway


def _article(**overrides) -> Article:
    defaults = dict(
        id="a1",
        headline="Acme beats earnings",
        summary="Acme reported Q3 results above expectations.",
        source="finnhub",
        url="https://example.com/a1",
        published_at=datetime(2026, 9, 10, tzinfo=timezone.utc),
    )
    defaults.update(overrides)
    return Article(**defaults)


def test_article_requires_all_fields():
    with pytest.raises(ValidationError):
        Article(id="a1")


def test_article_accepts_valid_payload():
    article = _article()

    assert article.id == "a1"
    assert article.source == "finnhub"


def test_takeaway_holds_supporting_article_ids():
    takeaway = Takeaway(text="Revenue grew 12% YoY", article_ids=["a1", "a2"])

    assert takeaway.article_ids == ["a1", "a2"]


def test_stock_summary_defaults_status_to_ok():
    summary = StockSummary(
        ticker="ACME",
        overall_sentiment="positive",
        takeaways=[Takeaway(text="Strong quarter", article_ids=["a1"])],
        risk_note="Guidance was not raised.",
        articles=[_article()],
        source_provider="finnhub",
    )

    assert summary.summary_status == "ok"


def test_stock_summary_rejects_invalid_status():
    with pytest.raises(ValidationError):
        StockSummary(
            ticker="ACME",
            overall_sentiment="positive",
            takeaways=[],
            risk_note="none",
            articles=[],
            source_provider="finnhub",
            summary_status="broken",
        )
