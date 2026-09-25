from typing import Literal

from pydantic import BaseModel, Field

from app.domain.models import Takeaway


class SummarizerOutput(BaseModel):
    overall_sentiment: Literal["positive", "negative", "neutral", "mixed"]
    takeaways: list[Takeaway] = Field(min_length=1, max_length=5)
    risk_note: str
