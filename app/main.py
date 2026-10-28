import logging
import sys
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from app.api.orders import router as orders_router
from app.core.config import get_settings
from app.db.database import engine

settings = get_settings()
logging.basicConfig(
    level=getattr(logging, settings.log_level.upper(), logging.INFO),
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
    stream=sys.stdout,
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(_: FastAPI):
    logger.info("service_started environment=%s", settings.environment)
    yield
    await engine.dispose()
    logger.info("service_stopped")


app = FastAPI(title=settings.app_name, version="1.0.0", lifespan=lifespan)
app.include_router(orders_router)


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(
    _: Request, exc: RequestValidationError
) -> JSONResponse:
    return JSONResponse(status_code=422, content={"detail": exc.errors()})


@app.exception_handler(SQLAlchemyError)
async def database_exception_handler(_: Request, exc: SQLAlchemyError) -> JSONResponse:
    logger.error("database_error error_type=%s", type(exc).__name__)
    return JSONResponse(status_code=500, content={"detail": "Database operation failed"})


@app.get("/health", tags=["health"])
async def health() -> JSONResponse:
    try:
        async with engine.connect() as connection:
            await connection.execute(text("SELECT 1"))
        return JSONResponse(content={"status": "healthy", "database": "connected"})
    except SQLAlchemyError as exc:
        logger.error("health_check_database_unavailable error_type=%s", type(exc).__name__)
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={"status": "unhealthy", "database": "disconnected"},
        )
