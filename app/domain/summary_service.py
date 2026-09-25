from app.domain.models import Article, StockSummary
from app.domain.ports import NewsProvider, Summarizer


class SummaryService:
    def __init__(
        self,
        news_provider: NewsProvider,
        summarizer: Summarizer,
        max_articles: int,
    ) -> None:
        self._news_provider = news_provider
        self._summarizer = summarizer
        self._max_articles = max_articles

    async def get_summary(self, ticker: str) -> StockSummary:
        news = await self._news_provider.fetch(ticker)
        articles = self._dedupe_and_order(news.articles)[: self._max_articles]

        if not articles:
            return StockSummary(
                ticker=ticker,
                overall_sentiment="neutral",
                takeaways=[],
                risk_note=f"No recent news found for {ticker}.",
                articles=[],
                source_provider=news.source_provider,
                summary_status="ok",
            )

        summary = await self._summarizer.summarize(ticker, articles)
        return summary.model_copy(update={"source_provider": news.source_provider})

    @staticmethod
    def _dedupe_and_order(articles: list[Article]) -> list[Article]:
        seen: set[str] = set()
        deduped = []
        for article in articles:
            if article.id in seen:
                continue
            seen.add(article.id)
            deduped.append(article)
        return sorted(deduped, key=lambda a: a.published_at, reverse=True)
