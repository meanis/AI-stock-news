from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.dependencies import get_settings
from app.api.routes import router


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Fail at startup, not on the first request, when required settings are missing.
    get_settings()
    yield


app = FastAPI(title="AI-stock-news", lifespan=lifespan)
app.include_router(router)
