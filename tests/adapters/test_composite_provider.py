from datetime import datetime, timezone

import pytest

from app.adapters.news.composite import CompositeNewsProvider
from app.domain.models import Article, NewsResult


def _article(article_id: str) -> Article:
    return Article(
        id=article_id,
        headline=f"Headline {article_id}",
        summary="Summary",
        source="Some Source",
        url=f"https://example.com/{article_id}",
        published_at=datetime(2024, 9, 10, tzinfo=timezone.utc),
    )


class _FakeProvider:
    def __init__(self, name, articles=None, error=None):
        self._name = name
        self._articles = articles if articles is not None else []
        self._error = error

    async def fetch(self, ticker: str) -> NewsResult:
        if self._error is not None:
            raise self._error
        return NewsResult(articles=self._articles, source_provider=self._name)


@pytest.mark.asyncio
async def test_fetch_returns_primary_articles_and_records_primary_as_source():
    primary = _FakeProvider("finnhub", articles=[_article("p1")])
    secondary = _FakeProvider("alphavantage", articles=[_article("s1")])
    composite = CompositeNewsProvider(primary=primary, secondary=secondary)

    result = await composite.fetch("ACME")

    assert [a.id for a in result.articles] == ["p1"]
    assert result.source_provider == "finnhub"


@pytest.mark.asyncio
async def test_fetch_falls_back_to_secondary_when_primary_returns_empty():
    primary = _FakeProvider("finnhub", articles=[])
    secondary = _FakeProvider("alphavantage", articles=[_article("s1")])
    composite = CompositeNewsProvider(primary=primary, secondary=secondary)

    result = await composite.fetch("ACME")

    assert [a.id for a in result.articles] == ["s1"]
    assert result.source_provider == "alphavantage"


@pytest.mark.asyncio
async def test_fetch_falls_back_to_secondary_when_primary_raises():
    primary = _FakeProvider("finnhub", error=RuntimeError("primary down"))
    secondary = _FakeProvider("alphavantage", articles=[_article("s1")])
    composite = CompositeNewsProvider(primary=primary, secondary=secondary)

    result = await composite.fetch("ACME")

    assert [a.id for a in result.articles] == ["s1"]
    assert result.source_provider == "alphavantage"


@pytest.mark.asyncio
async def test_fetch_propagates_primary_error_when_no_secondary_configured():
    primary = _FakeProvider("finnhub", error=RuntimeError("primary down"))
    composite = CompositeNewsProvider(primary=primary)

    with pytest.raises(RuntimeError, match="primary down"):
        await composite.fetch("ACME")


@pytest.mark.asyncio
async def test_fetch_propagates_secondary_error_when_both_fail():
    primary = _FakeProvider("finnhub", error=RuntimeError("primary down"))
    secondary = _FakeProvider("alphavantage", error=RuntimeError("secondary down"))
    composite = CompositeNewsProvider(primary=primary, secondary=secondary)

    with pytest.raises(RuntimeError, match="secondary down"):
        await composite.fetch("ACME")
