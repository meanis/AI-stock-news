from app.config import Settings


def test_settings_loads_required_and_default_values(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
    monkeypatch.setenv("FINNHUB_API_KEY", "finnhub-test")
    monkeypatch.delenv("ALPHAVANTAGE_API_KEY", raising=False)
    monkeypatch.delenv("OPENAI_MODEL", raising=False)
    monkeypatch.delenv("NEWS_LOOKBACK_DAYS", raising=False)
    monkeypatch.delenv("MAX_ARTICLES", raising=False)

    settings = Settings(_env_file=None)

    assert settings.openai_api_key == "sk-test"
    assert settings.finnhub_api_key == "finnhub-test"
    assert settings.alphavantage_api_key is None
    assert settings.openai_model == "gpt-4o-mini"
    assert settings.news_lookback_days == 7
    assert settings.max_articles == 10


def test_settings_reads_optional_and_overridden_values(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
    monkeypatch.setenv("FINNHUB_API_KEY", "finnhub-test")
    monkeypatch.setenv("ALPHAVANTAGE_API_KEY", "av-test")
    monkeypatch.setenv("OPENAI_MODEL", "gpt-4o")
    monkeypatch.setenv("NEWS_LOOKBACK_DAYS", "3")
    monkeypatch.setenv("MAX_ARTICLES", "5")

    settings = Settings(_env_file=None)

    assert settings.alphavantage_api_key == "av-test"
    assert settings.openai_model == "gpt-4o"
    assert settings.news_lookback_days == 3
    assert settings.max_articles == 5
