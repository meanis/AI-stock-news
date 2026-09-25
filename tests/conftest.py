import pytest

from app.api.dependencies import get_settings, get_summary_service


@pytest.fixture(autouse=True)
def _reset_dependency_caches():
    # Both are lru_cache'd process-wide singletons; without this, whichever test
    # resolves them first pins its (often monkeypatched) settings for the whole run.
    get_settings.cache_clear()
    get_summary_service.cache_clear()
    yield
    get_settings.cache_clear()
    get_summary_service.cache_clear()
