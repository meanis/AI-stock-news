from datetime import datetime
from typing import Literal

from pydantic import BaseModel


class Article(BaseModel):
    id: str
    headline: str
    summary: str
    source: str
    url: str
    published_at: datetime


class Takeaway(BaseModel):
    text: str
    article_ids: list[str]


class NewsResult(BaseModel):
    articles: list[Article]
    source_provider: str


class StockSummary(BaseModel):
    ticker: str
    overall_sentiment: str
    takeaways: list[Takeaway]
    risk_note: str
    articles: list[Article]
    source_provider: str
    summary_status: Literal["ok", "degraded"] = "ok"
