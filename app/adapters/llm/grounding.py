from app.adapters.llm.schema import SummarizerOutput


class GroundingError(Exception):
    pass


def validate_grounding(draft: SummarizerOutput, known_article_ids: set[str]) -> None:
    for takeaway in draft.takeaways:
        if not takeaway.article_ids:
            raise GroundingError(f"takeaway cites no articles: {takeaway.text!r}")
        for article_id in takeaway.article_ids:
            if article_id not in known_article_ids:
                raise GroundingError(
                    f"takeaway cites unknown article id: {article_id!r}"
                )
