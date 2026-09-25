import json
from datetime import datetime, timezone
from pathlib import Path

from app.adapters.news.mapper import map_alphavantage_articles

FIXTURE = Path(__file__).parent.parent / "fixtures" / "alphavantage_news_sentiment.json"


def _load_feed() -> list[dict]:
    return json.loads(FIXTURE.read_text())["feed"]


def test_maps_valid_items_onto_article_fields():
    raw = _load_feed()

    articles = map_alphavantage_articles(raw)

    valid_ids = {a.id for a in articles}
    assert "ea2208a171a70777" in valid_ids
    assert "5fc856127f0b77fa" in valid_ids

    first = next(a for a in articles if a.id == "ea2208a171a70777")
    assert first.headline == "Acme Corp shares rally on strong guidance"
    assert first.summary == "Acme Corp shares rose after management raised full-year guidance."
    assert first.source == "Zacks Commentary"
    assert first.url == "https://example.com/av/acme-rally"
    assert first.published_at == datetime(2024, 9, 10, 14, 30, 0, tzinfo=timezone.utc)


def test_skips_items_missing_required_fields():
    raw = _load_feed()

    articles = map_alphavantage_articles(raw)

    assert len(articles) == 2


def test_empty_input_returns_empty_list():
    assert map_alphavantage_articles([]) == []


def test_mapped_articles_have_unique_ids():
    raw = _load_feed()

    articles = map_alphavantage_articles(raw)

    ids = [a.id for a in articles]
    assert len(ids) == len(set(ids))


def test_skips_item_with_non_string_url():
    raw = [
        {
            "title": "Bad url item",
            "summary": "Should be skipped",
            "source": "Wire Service",
            "url": 12345,
            "time_published": "20240908T080000",
        }
    ]

    assert map_alphavantage_articles(raw) == []
