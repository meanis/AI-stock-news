from typing import Protocol, runtime_checkable

from app.domain.models import Article, NewsResult, StockSummary


@runtime_checkable
class NewsProvider(Protocol):
    async def fetch(self, ticker: str) -> NewsResult: ...


@runtime_checkable
class Summarizer(Protocol):
    async def summarize(self, ticker: str, articles: list[Article]) -> StockSummary: ...
