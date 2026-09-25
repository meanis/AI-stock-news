import hashlib
from datetime import datetime, timezone

from app.domain.models import Article

_REQUIRED_FIELDS = ("id", "headline", "summary", "source", "url", "datetime")
_AV_REQUIRED_FIELDS = ("title", "summary", "source", "url", "time_published")


def map_finnhub_articles(raw: list[dict]) -> list[Article]:
    articles = []
    for item in raw:
        if any(field not in item or item[field] in (None, "") for field in _REQUIRED_FIELDS):
            continue
        try:
            published_at = datetime.fromtimestamp(item["datetime"], tz=timezone.utc)
        except (TypeError, ValueError, OSError, OverflowError):
            continue
        articles.append(
            Article(
                id=str(item["id"]),
                headline=item["headline"],
                summary=item["summary"],
                source=item["source"],
                url=item["url"],
                published_at=published_at,
            )
        )
    return articles


def map_alphavantage_articles(raw: list[dict]) -> list[Article]:
    articles = []
    for item in raw:
        if any(field not in item or item[field] in (None, "") for field in _AV_REQUIRED_FIELDS):
            continue
        try:
            published_at = datetime.strptime(item["time_published"], "%Y%m%dT%H%M%S").replace(
                tzinfo=timezone.utc
            )
            article_id = hashlib.sha1(item["url"].encode()).hexdigest()[:16]
        except (TypeError, ValueError, AttributeError):
            continue
        articles.append(
            Article(
                id=article_id,
                headline=item["title"],
                summary=item["summary"],
                source=item["source"],
                url=item["url"],
                published_at=published_at,
            )
        )
    return articles
