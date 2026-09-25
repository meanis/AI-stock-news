import json
from datetime import datetime, timezone
from pathlib import Path

import httpx
import pytest
import respx

from app.adapters.llm.openai_summarizer import OpenAISummarizer
from app.domain.models import Article

FIXTURE = Path(__file__).parent.parent / "fixtures" / "openai_chat_completion.json"
BASE_URL = "https://api.openai.com/v1"


def _summarizer() -> OpenAISummarizer:
    return OpenAISummarizer(api_key="test-key", model="gpt-4o-mini", base_url=BASE_URL)


def _articles() -> list[Article]:
    return [
        Article(
            id="a1",
            headline="Acme beats earnings",
            summary="Acme reported Q3 results above expectations.",
            source="Reuters",
            url="https://example.com/a1",
            published_at=datetime(2024, 9, 10, tzinfo=timezone.utc),
        )
    ]


def _mock_completion(content: dict | str, status_code: int = 200):
    if isinstance(content, dict):
        content = json.dumps(content)
    body = json.loads(FIXTURE.read_text())
    body["choices"][0]["message"]["content"] = content
    respx.post(f"{BASE_URL}/chat/completions").mock(
        return_value=httpx.Response(status_code, json=body)
    )


@pytest.mark.asyncio
@respx.mock
async def test_summarize_sends_temperature_zero_and_json_response_format():
    route = respx.post(f"{BASE_URL}/chat/completions").mock(
        return_value=httpx.Response(200, json=json.loads(FIXTURE.read_text()))
    )

    await _summarizer().summarize("ACME", _articles())

    assert route.called
    body = json.loads(route.calls.last.request.content)
    assert body["model"] == "gpt-4o-mini"
    assert body["temperature"] == 0
    assert body["response_format"] == {"type": "json_object"}
    assert "max_tokens" in body
    assert "a1" in json.dumps(body["messages"])


@pytest.mark.asyncio
@respx.mock
async def test_summarize_returns_ok_summary_on_valid_response():
    respx.post(f"{BASE_URL}/chat/completions").mock(
        return_value=httpx.Response(200, json=json.loads(FIXTURE.read_text()))
    )

    result = await _summarizer().summarize("ACME", _articles())

    assert result.summary_status == "ok"
    assert result.ticker == "ACME"
    assert result.overall_sentiment == "positive"
    assert result.risk_note == "Guidance was not raised."
    assert result.takeaways[0].article_ids == ["a1"]
    assert result.articles == _articles()
    assert result.source_provider == "openai"


@pytest.mark.asyncio
@respx.mock
async def test_summarize_returns_degraded_on_malformed_json_content():
    _mock_completion(content="not valid json")

    result = await _summarizer().summarize("ACME", _articles())

    assert result.summary_status == "degraded"
    assert result.overall_sentiment == "unknown"
    assert result.takeaways == []
    assert result.articles == _articles()


@pytest.mark.asyncio
@respx.mock
async def test_summarize_logs_warning_when_degrading(caplog):
    respx.post(f"{BASE_URL}/chat/completions").mock(
        return_value=httpx.Response(401, json={"error": "invalid api key"})
    )

    with caplog.at_level("WARNING"):
        result = await _summarizer().summarize("ACME", _articles())

    assert result.summary_status == "degraded"
    assert any("summariz" in record.message.lower() for record in caplog.records)


@pytest.mark.asyncio
@respx.mock
async def test_summarize_returns_degraded_on_unknown_article_id_citation():
    _mock_completion(
        content={
            "overall_sentiment": "positive",
            "takeaways": [{"text": "Bad citation", "article_ids": ["unknown-id"]}],
            "risk_note": "none",
        }
    )

    result = await _summarizer().summarize("ACME", _articles())

    assert result.summary_status == "degraded"


@pytest.mark.asyncio
@respx.mock
async def test_summarize_returns_degraded_on_non_200_response():
    respx.post(f"{BASE_URL}/chat/completions").mock(
        return_value=httpx.Response(500, json={"error": "boom"})
    )

    result = await _summarizer().summarize("ACME", _articles())

    assert result.summary_status == "degraded"


@pytest.mark.asyncio
@respx.mock
async def test_summarize_returns_degraded_on_timeout():
    respx.post(f"{BASE_URL}/chat/completions").mock(side_effect=httpx.TimeoutException("timed out"))

    result = await _summarizer().summarize("ACME", _articles())

    assert result.summary_status == "degraded"


@pytest.mark.asyncio
@respx.mock
async def test_summarize_returns_degraded_on_unexpected_response_shape():
    respx.post(f"{BASE_URL}/chat/completions").mock(
        return_value=httpx.Response(200, json=["not", "the", "expected", "shape"])
    )

    result = await _summarizer().summarize("ACME", _articles())

    assert result.summary_status == "degraded"
