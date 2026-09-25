from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    openai_api_key: str
    openai_model: str = "gpt-4o-mini"
    finnhub_api_key: str
    alphavantage_api_key: str | None = None
    news_lookback_days: int = 7
    max_articles: int = 10
