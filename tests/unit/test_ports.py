from datetime import datetime, timezone

from app.domain.models import Article, NewsResult, StockSummary, Takeaway
from app.domain.ports import NewsProvider, Summarizer


class FakeNewsProvider:
    async def fetch(self, ticker: str) -> NewsResult:
        return NewsResult(articles=[], source_provider="fake")


class FakeSummarizer:
    async def summarize(self, ticker: str, articles: list[Article]) -> StockSummary:
        return StockSummary(
            ticker=ticker,
            overall_sentiment="neutral",
            takeaways=[Takeaway(text="stub", article_ids=[])],
            risk_note="stub",
            articles=articles,
            source_provider="fake",
        )


class NotAProvider:
    pass


def test_fake_news_provider_satisfies_protocol():
    assert isinstance(FakeNewsProvider(), NewsProvider)


def test_fake_summarizer_satisfies_protocol():
    assert isinstance(FakeSummarizer(), Summarizer)


def test_class_missing_method_does_not_satisfy_protocol():
    assert not isinstance(NotAProvider(), NewsProvider)
    assert not isinstance(NotAProvider(), Summarizer)
