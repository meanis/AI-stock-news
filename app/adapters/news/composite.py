from app.domain.models import NewsResult
from app.domain.ports import NewsProvider


class CompositeNewsProvider:
    def __init__(self, primary: NewsProvider, secondary: NewsProvider | None = None) -> None:
        self._primary = primary
        self._secondary = secondary

    async def fetch(self, ticker: str) -> NewsResult:
        try:
            result = await self._primary.fetch(ticker)
        except Exception:
            if self._secondary is None:
                raise
            return await self._secondary.fetch(ticker)

        if result.articles or self._secondary is None:
            return result

        return await self._secondary.fetch(ticker)
