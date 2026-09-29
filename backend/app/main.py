import asyncio
import json
import logging
import re
import time
from contextlib import asynccontextmanager
from typing import Literal
from uuid import uuid4

import psycopg
from fastapi import FastAPI
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from app.config import get_settings
from app.db import engine
from app.errors import error_response, install_handlers
from app.routes import router

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield
    engine.dispose()


app = FastAPI(title="Учёт оборудования", version="0.1.0", lifespan=lifespan)
app.include_router(router)
install_handlers(app)


@app.middleware("http")
async def request_context(request, call_next):
    candidate = request.headers.get("x-request-id", "")
    request.state.request_id = (
        candidate if re.fullmatch(r"[A-Za-z0-9_-]{1,64}", candidate) else uuid4().hex
    )
    started = time.monotonic()
    try:
        response = await call_next(request)
    except Exception as exc:
        logger.error("Unhandled request error (%s)", type(exc).__name__)
        response = error_response(request, 500, "internal_error", "Внутренняя ошибка сервера")
    response.headers["X-Request-ID"] = request.state.request_id
    route = request.scope.get("route")
    logging.getLogger("uvicorn.error").info(
        json.dumps(
            {
                "request_id": request.state.request_id,
                "method": request.method,
                "route": getattr(route, "path", "unmatched"),
                "status": response.status_code,
                "duration_ms": round((time.monotonic() - started) * 1000, 2),
            }
        )
    )
    return response


class Status(BaseModel):
    service: str = "equipment-api"
    version: str = "0.1.0"
    status: Literal["ok"] = "ok"


@app.get("/api/v1/status", response_model=Status, tags=["System"])
def status() -> Status:
    return Status()


@app.get("/health/live", tags=["Health"])
def live() -> dict[str, str]:
    return {"status": "alive"}


@app.get("/health/ready", tags=["Health"])
async def ready():
    settings = get_settings()
    # Async is limited to this probe so its whole network roundtrip has a deadline.
    # Business handlers and SQLAlchemy sessions remain synchronous.
    url = settings.sqlalchemy_url
    connection = None
    try:
        async with asyncio.timeout(settings.readiness_timeout):
            connection = await psycopg.AsyncConnection.connect(
                url.set(drivername="postgresql").render_as_string(hide_password=False),
                autocommit=True,
            )
            await connection.execute("SELECT 1")
        return {"status": "ready", "database": "connected"}
    except psycopg.Error, TimeoutError:
        logger.warning("Database readiness check failed")
        return JSONResponse(status_code=503, content={"status": "not_ready"})
    finally:
        if connection is not None:
            await connection.close()
