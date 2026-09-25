from functools import lru_cache

from app.adapters.llm.openai_summarizer import OpenAISummarizer
from app.adapters.news.alphavantage import AlphaVantageNewsProvider
from app.adapters.news.composite import CompositeNewsProvider
from app.adapters.news.finnhub import FinnhubNewsProvider
from app.config import Settings
from app.domain.summary_service import SummaryService


@lru_cache
def get_settings() -> Settings:
    return Settings()


@lru_cache
def get_summary_service() -> SummaryService:
    settings = get_settings()
    primary = FinnhubNewsProvider(
        api_key=settings.finnhub_api_key, lookback_days=settings.news_lookback_days
    )
    secondary = None
    if settings.alphavantage_api_key:
        secondary = AlphaVantageNewsProvider(
            api_key=settings.alphavantage_api_key, lookback_days=settings.news_lookback_days
        )
    news_provider = CompositeNewsProvider(primary=primary, secondary=secondary)
    summarizer = OpenAISummarizer(api_key=settings.openai_api_key, model=settings.openai_model)
    return SummaryService(
        news_provider=news_provider,
        summarizer=summarizer,
        max_articles=settings.max_articles,
    )
