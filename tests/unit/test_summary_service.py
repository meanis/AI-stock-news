from datetime import datetime, timedelta, timezone

import pytest

from app.domain.models import Article, NewsResult, StockSummary, Takeaway
from app.domain.summary_service import SummaryService

_BASE_TIME = datetime(2024, 9, 10, tzinfo=timezone.utc)


def _article(article_id: str, days_old: int = 0) -> Article:
    return Article(
        id=article_id,
        headline=f"Headline {article_id}",
        summary="Summary",
        source="Some Source",
        url=f"https://example.com/{article_id}",
        published_at=_BASE_TIME - timedelta(days=days_old),
    )


class _FakeNewsProvider:
    def __init__(self, articles: list[Article], source_provider: str = "finnhub"):
        self._articles = articles
        self._source_provider = source_provider

    async def fetch(self, ticker: str) -> NewsResult:
        return NewsResult(articles=self._articles, source_provider=self._source_provider)


class _StubSummarizer:
    def __init__(self, response: StockSummary):
        self._response = response
        self.calls: list[tuple[str, list[Article]]] = []

    async def summarize(self, ticker: str, articles: list[Article]) -> StockSummary:
        self.calls.append((ticker, articles))
        return self._response


def _stub_response(ticker: str, articles: list[Article]) -> StockSummary:
    return StockSummary(
        ticker=ticker,
        overall_sentiment="positive",
        takeaways=[Takeaway(text="stub takeaway", article_ids=[a.id for a in articles])],
        risk_note="stub risk",
        articles=articles,
        source_provider="openai",
        summary_status="ok",
    )


@pytest.mark.asyncio
async def test_dedupes_and_orders_articles_before_summarizing():
    newest = _article("a2", days_old=0)
    oldest = _article("a1", days_old=5)
    duplicate_of_oldest = _article("a1", days_old=5)
    provider = _FakeNewsProvider([oldest, newest, duplicate_of_oldest])
    summarizer = _StubSummarizer(_stub_response("ACME", [oldest, newest]))
    service = SummaryService(news_provider=provider, summarizer=summarizer, max_articles=10)

    await service.get_summary("ACME")

    assert len(summarizer.calls) == 1
    _, articles = summarizer.calls[0]
    assert [a.id for a in articles] == ["a2", "a1"]


@pytest.mark.asyncio
async def test_caps_article_count_before_summarizing():
    articles = [_article(f"a{i}", days_old=i) for i in range(5)]
    provider = _FakeNewsProvider(articles)
    summarizer = _StubSummarizer(_stub_response("ACME", articles[:2]))
    service = SummaryService(news_provider=provider, summarizer=summarizer, max_articles=2)

    result = await service.get_summary("ACME")

    _, called_with = summarizer.calls[0]
    assert [a.id for a in called_with] == ["a0", "a1"]
    assert [a.id for a in result.articles] == ["a0", "a1"]


@pytest.mark.asyncio
async def test_returns_no_news_summary_without_calling_summarizer_when_no_articles():
    provider = _FakeNewsProvider([], source_provider="finnhub")
    summarizer = _StubSummarizer(_stub_response("ACME", []))
    service = SummaryService(news_provider=provider, summarizer=summarizer, max_articles=10)

    result = await service.get_summary("ACME")

    assert summarizer.calls == []
    assert result.overall_sentiment == "neutral"
    assert result.takeaways == []
    assert result.articles == []
    assert result.summary_status == "ok"
    assert "ACME" in result.risk_note


@pytest.mark.asyncio
async def test_overwrites_source_provider_with_the_news_result_source():
    articles = [_article("a1")]
    provider = _FakeNewsProvider(articles, source_provider="alphavantage")
    summarizer = _StubSummarizer(_stub_response("ACME", articles))
    service = SummaryService(news_provider=provider, summarizer=summarizer, max_articles=10)

    result = await service.get_summary("ACME")

    assert result.source_provider == "alphavantage"
