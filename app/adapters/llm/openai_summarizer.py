import json
import logging

import httpx
from pydantic import ValidationError

from app.adapters import http_client
from app.adapters.llm.grounding import GroundingError, validate_grounding
from app.adapters.llm.schema import SummarizerOutput
from app.domain.models import Article, StockSummary

logger = logging.getLogger(__name__)

_MAX_ARTICLE_SUMMARY_CHARS = 500
_MAX_COMPLETION_TOKENS = 500
_DEFAULT_TIMEOUT_SECONDS = 30.0

_SYSTEM_PROMPT = (
    "You are a financial news summarizer. You will be given a numbered list of "
    "news articles about a stock ticker. Using ONLY the information in those "
    "articles, respond with a JSON object with this exact shape: "
    '{"overall_sentiment": "positive" | "negative" | "neutral" | "mixed", "takeaways": '
    '[{"text": string, "article_ids": [string, ...]}, ...], "risk_note": string}. '
    "Every takeaway must cite at least one article, and every id in article_ids must "
    "be one of the numbered article ids given below. "
    "Provide 3-5 takeaways when enough material exists, and never more than 5."
)


def _truncate(text: str, limit: int = _MAX_ARTICLE_SUMMARY_CHARS) -> str:
    return text if len(text) <= limit else text[:limit] + "..."


def _build_user_message(ticker: str, articles: list[Article]) -> str:
    lines = [f"Ticker: {ticker}", "Articles:"]
    for article in articles:
        lines.append(f"[{article.id}] {article.headline} — {_truncate(article.summary)}")
    return "\n".join(lines)


def _degraded_summary(ticker: str, articles: list[Article]) -> StockSummary:
    return StockSummary(
        ticker=ticker,
        overall_sentiment="unknown",
        takeaways=[],
        risk_note="Summary unavailable; showing headlines only.",
        articles=articles,
        source_provider="openai",
        summary_status="degraded",
    )


class OpenAISummarizer:
    def __init__(
        self,
        api_key: str,
        model: str,
        base_url: str = "https://api.openai.com/v1",
        http_client: httpx.AsyncClient | None = None,
        timeout: float = _DEFAULT_TIMEOUT_SECONDS,
    ) -> None:
        self._api_key = api_key
        self._model = model
        self._base_url = base_url
        self._http_client = http_client
        self._timeout = timeout

    async def summarize(self, ticker: str, articles: list[Article]) -> StockSummary:
        payload = {
            "model": self._model,
            "temperature": 0,
            "max_tokens": _MAX_COMPLETION_TOKENS,
            "response_format": {"type": "json_object"},
            "messages": [
                {"role": "system", "content": _SYSTEM_PROMPT},
                {"role": "user", "content": _build_user_message(ticker, articles)},
            ],
        }

        try:
            response = await http_client.post(
                self._http_client,
                f"{self._base_url}/chat/completions",
                payload,
                headers={"Authorization": f"Bearer {self._api_key}"},
                timeout=self._timeout,
            )
            content = response.json()["choices"][0]["message"]["content"]
            draft = SummarizerOutput.model_validate_json(content)
            validate_grounding(draft, known_article_ids={a.id for a in articles})
        except (
            httpx.HTTPError,
            json.JSONDecodeError,
            ValidationError,
            GroundingError,
            KeyError,
            IndexError,
            TypeError,
        ) as exc:
            logger.warning("Summarizer degraded for ticker %s: %s", ticker, exc)
            return _degraded_summary(ticker, articles)

        return StockSummary(
            ticker=ticker,
            overall_sentiment=draft.overall_sentiment,
            takeaways=draft.takeaways,
            risk_note=draft.risk_note,
            articles=articles,
            source_provider="openai",
            summary_status="ok",
        )
