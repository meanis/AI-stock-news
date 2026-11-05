import time
from collections import OrderedDict
from collections.abc import Callable

from app.domain.models import Article, StockSummary
from app.domain.ports import Summarizer

_CacheKey = tuple[str, tuple[str, ...]]


class CachingSummarizer:
    """In-memory TTL cache in front of another Summarizer.

    Keyed on ticker plus the exact article ids, so fresh news naturally misses the
    cache; the TTL is only a backstop. Degraded summaries are never cached so a
    transient LLM failure is retried on the next request.
    """

    def __init__(
        self,
        inner: Summarizer,
        ttl_seconds: float,
        max_entries: int,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self._inner = inner
        self._ttl_seconds = ttl_seconds
        self._max_entries = max_entries
        self._clock = clock
        self._entries: OrderedDict[_CacheKey, tuple[float, StockSummary]] = OrderedDict()

    async def summarize(self, ticker: str, articles: list[Article]) -> StockSummary:
        if self._ttl_seconds <= 0:
            return await self._inner.summarize(ticker, articles)

        key = (ticker.upper(), tuple(a.id for a in articles))
        cached = self._entries.get(key)
        if cached is not None:
            expires_at, summary = cached
            if self._clock() < expires_at:
                return summary
            del self._entries[key]

        summary = await self._inner.summarize(ticker, articles)
        if summary.summary_status == "ok":
            self._entries[key] = (self._clock() + self._ttl_seconds, summary)
            while len(self._entries) > self._max_entries:
                self._entries.popitem(last=False)
        return summary
