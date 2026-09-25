import pytest

from app.adapters.llm.grounding import GroundingError, validate_grounding
from app.adapters.llm.schema import SummarizerOutput
from app.domain.models import Takeaway


def test_passes_when_all_article_ids_are_known():
    draft = SummarizerOutput(
        overall_sentiment="positive",
        takeaways=[Takeaway(text="Strong quarter", article_ids=["a1", "a2"])],
        risk_note="none",
    )

    validate_grounding(draft, known_article_ids={"a1", "a2", "a3"})


def test_raises_when_a_takeaway_cites_an_unknown_article_id():
    draft = SummarizerOutput(
        overall_sentiment="positive",
        takeaways=[Takeaway(text="Strong quarter", article_ids=["a1", "unknown-id"])],
        risk_note="none",
    )

    with pytest.raises(GroundingError):
        validate_grounding(draft, known_article_ids={"a1", "a2"})


def test_raises_when_a_takeaway_cites_no_articles():
    draft = SummarizerOutput(
        overall_sentiment="positive",
        takeaways=[Takeaway(text="Uncited claim", article_ids=[])],
        risk_note="none",
    )

    with pytest.raises(GroundingError):
        validate_grounding(draft, known_article_ids={"a1"})
