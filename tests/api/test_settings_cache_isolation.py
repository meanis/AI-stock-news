from app.api.dependencies import get_settings


def _set_keys(monkeypatch, openai_key: str) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", openai_key)
    monkeypatch.setenv("FINNHUB_API_KEY", "finnhub-test")


# These two tests are order-dependent on purpose: the second only passes if the
# cache populated by the first does not leak into it.
def test_first_test_populates_the_settings_cache(monkeypatch):
    _set_keys(monkeypatch, "first")

    assert get_settings().openai_api_key == "first"


def test_second_test_sees_its_own_settings_not_a_stale_cache(monkeypatch):
    _set_keys(monkeypatch, "second")

    assert get_settings().openai_api_key == "second"
