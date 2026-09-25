import logging
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse

from app.api.dependencies import get_summary_service
from app.domain.models import StockSummary
from app.domain.summary_service import SummaryService

logger = logging.getLogger(__name__)

router = APIRouter()
INDEX_PAGE = Path(__file__).resolve().parent.parent / "static" / "index.html"


@router.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/")
async def index() -> FileResponse:
    return FileResponse(INDEX_PAGE)


@router.get("/api/summary/{ticker}", response_model=StockSummary)
async def get_summary(
    ticker: str, service: SummaryService = Depends(get_summary_service)
) -> StockSummary:
    ticker = ticker.strip().upper()
    try:
        return await service.get_summary(ticker)
    except Exception:
        logger.warning("News provider unavailable for ticker %s", ticker, exc_info=True)
        raise HTTPException(status_code=503, detail="News provider unavailable")
