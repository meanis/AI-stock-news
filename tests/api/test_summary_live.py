import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from app.config import Settings
from app.main import app


def _real_settings_available() -> bool:
    try:
        Settings()
        return True
    except ValidationError:
        return False


@pytest.mark.live
@pytest.mark.skipif(
    not _real_settings_available(),
    reason="requires real FINNHUB_API_KEY and OPENAI_API_KEY (env or .env)",
)
def test_get_summary_hits_real_finnhub_and_openai():
    client = TestClient(app)

    response = client.get("/api/summary/AAPL")

    assert response.status_code == 200
    body = response.json()
    assert body["ticker"] == "AAPL"
    # "degraded" would mean the OpenAI call failed (bad key, quota, model), which is
    # exactly what a live smoke test exists to catch.
    assert body["summary_status"] == "ok"
    assert body["articles"]
    assert body["takeaways"]
