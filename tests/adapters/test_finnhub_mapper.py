import json
from datetime import datetime, timezone
from pathlib import Path

from app.adapters.news.mapper import map_finnhub_articles

FIXTURE = Path(__file__).parent.parent / "fixtures" / "finnhub_company_news.json"


def _load_fixture() -> list[dict]:
    return json.loads(FIXTURE.read_text())


def test_maps_valid_items_onto_article_fields():
    raw = _load_fixture()

    articles = map_finnhub_articles(raw)

    valid_ids = {a.id for a in articles}
    assert "111000111" in valid_ids
    assert "111000112" in valid_ids

    first = next(a for a in articles if a.id == "111000111")
    assert first.headline == "Acme Corp beats Q3 earnings expectations"
    assert first.summary == "Acme Corp reported Q3 revenue above analyst estimates, driven by strong demand."
    assert first.source == "Reuters"
    assert first.url == "https://example.com/news/acme-q3-earnings"
    assert first.published_at == datetime(2024, 9, 10, 16, 0, tzinfo=timezone.utc)


def test_skips_items_missing_required_fields():
    raw = _load_fixture()

    articles = map_finnhub_articles(raw)

    assert "111000113" not in {a.id for a in articles}
    assert len(articles) == 2


def test_empty_input_returns_empty_list():
    assert map_finnhub_articles([]) == []


def test_skips_item_with_out_of_range_datetime():
    raw = [
        {
            "id": 999,
            "headline": "Bad timestamp item",
            "summary": "Should be skipped",
            "source": "Wire Service",
            "url": "https://example.com/news/bad-timestamp",
            "datetime": 10**20,
        }
    ]

    assert map_finnhub_articles(raw) == []
