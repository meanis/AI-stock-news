from datetime import datetime, timezone

import pytest

from app.adapters.llm.caching_summarizer import CachingSummarizer
from app.domain.models import Article, StockSummary


def _article(article_id: str) -> Article:
    return Article(
        id=article_id,
        headline=f"Headline {article_id}",
        summary="Summary",
        source="Some Source",
        url=f"https://example.com/{article_id}",
        published_at=datetime(2024, 9, 10, tzinfo=timezone.utc),
    )


class _CountingSummarizer:
    def __init__(self, summary_status: str = "ok"):
        self._summary_status = summary_status
        self.calls: list[tuple[str, list[Article]]] = []

    async def summarize(self, ticker: str, articles: list[Article]) -> StockSummary:
        self.calls.append((ticker, articles))
        return StockSummary(
            ticker=ticker,
            overall_sentiment="positive",
            takeaways=[],
            risk_note=f"call {len(self.calls)}",
            articles=articles,
            source_provider="openai",
            summary_status=self._summary_status,
        )


class _FakeClock:
    def __init__(self) -> None:
        self.now = 0.0

    def __call__(self) -> float:
        return self.now


def _caching(inner, ttl_seconds: float = 60, max_entries: int = 10, clock=None):
    return CachingSummarizer(
        inner, ttl_seconds=ttl_seconds, max_entries=max_entries, clock=clock or _FakeClock()
    )


@pytest.mark.asyncio
async def test_returns_cached_summary_for_same_ticker_and_articles():
    inner = _CountingSummarizer()
    summarizer = _caching(inner)
    articles = [_article("a1"), _article("a2")]

    first = await summarizer.summarize("ACME", articles)
    second = await summarizer.summarize("ACME", articles)

    assert len(inner.calls) == 1
    assert second == first


@pytest.mark.asyncio
async def test_ticker_key_is_case_insensitive():
    inner = _CountingSummarizer()
    summarizer = _caching(inner)
    articles = [_article("a1")]

    await summarizer.summarize("acme", articles)
    await summarizer.summarize("ACME", articles)

    assert len(inner.calls) == 1


@pytest.mark.asyncio
async def test_calls_inner_again_when_article_set_changes():
    inner = _CountingSummarizer()
    summarizer = _caching(inner)

    await summarizer.summarize("ACME", [_article("a1")])
    await summarizer.summarize("ACME", [_article("a2"), _article("a1")])

    assert len(inner.calls) == 2


@pytest.mark.asyncio
async def test_calls_inner_again_for_a_different_ticker():
    inner = _CountingSummarizer()
    summarizer = _caching(inner)
    articles = [_article("a1")]

    await summarizer.summarize("ACME", articles)
    await summarizer.summarize("INIT", articles)

    assert len(inner.calls) == 2


@pytest.mark.asyncio
async def test_entry_expires_after_ttl():
    inner = _CountingSummarizer()
    clock = _FakeClock()
    summarizer = _caching(inner, ttl_seconds=60, clock=clock)
    articles = [_article("a1")]

    await summarizer.summarize("ACME", articles)
    clock.now = 59.9
    await summarizer.summarize("ACME", articles)
    assert len(inner.calls) == 1

    clock.now = 60.0
    await summarizer.summarize("ACME", articles)
    assert len(inner.calls) == 2


@pytest.mark.asyncio
async def test_does_not_cache_degraded_summaries():
    inner = _CountingSummarizer(summary_status="degraded")
    summarizer = _caching(inner)
    articles = [_article("a1")]

    await summarizer.summarize("ACME", articles)
    await summarizer.summarize("ACME", articles)

    assert len(inner.calls) == 2


@pytest.mark.asyncio
async def test_evicts_oldest_entry_when_max_entries_reached():
    inner = _CountingSummarizer()
    summarizer = _caching(inner, max_entries=2)

    await summarizer.summarize("AAA", [_article("a1")])
    await summarizer.summarize("BBB", [_article("a1")])
    await summarizer.summarize("CCC", [_article("a1")])
    assert len(inner.calls) == 3

    await summarizer.summarize("CCC", [_article("a1")])
    await summarizer.summarize("BBB", [_article("a1")])
    assert len(inner.calls) == 3

    await summarizer.summarize("AAA", [_article("a1")])
    assert len(inner.calls) == 4


@pytest.mark.asyncio
async def test_zero_ttl_disables_caching():
    inner = _CountingSummarizer()
    summarizer = _caching(inner, ttl_seconds=0)
    articles = [_article("a1")]

    await summarizer.summarize("ACME", articles)
    await summarizer.summarize("ACME", articles)

    assert len(inner.calls) == 2
