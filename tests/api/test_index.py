from fastapi.testclient import TestClient

from app.main import app


def test_index_serves_the_summary_page():
    client = TestClient(app)

    response = client.get("/")

    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]
    page = response.text

    # Ticker form, with loading, error and result states wired to the summary API.
    assert 'id="ticker-form"' in page
    assert 'name="ticker"' in page
    assert 'id="loading"' in page
    assert 'id="error"' in page
    assert 'id="result"' in page
    assert "/api/summary/" in page

    # Citations are numbered by position in the article list, so the list must be ordered.
    assert '<ol id="result-articles">' in page
    assert "takeaway.article_ids" in page

    assert "not investment advice" in page.lower()
