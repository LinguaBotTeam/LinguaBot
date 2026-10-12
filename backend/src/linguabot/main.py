"""Точка входа приложения FastAPI."""

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from starlette.exceptions import HTTPException as StarletteHTTPException

from linguabot.api.v1.router import api_router
from linguabot.core.config import settings
from linguabot.core.errors import STATUS_CODE_MAP, APIError, error_payload
from linguabot.db.session import init_models


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_models()
    yield


app = FastAPI(title=settings.app_name, version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(APIError)
async def handle_api_error(request: Request, exc: APIError) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code,
        content=error_payload(exc.code, exc.message, exc.field),
    )


@app.exception_handler(RequestValidationError)
async def handle_validation_error(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    errors = exc.errors()
    first = errors[0] if errors else {}
    location = [
        part
        for part in first.get("loc", ())
        if part not in ("body", "query", "path")
    ]
    field = str(location[-1]) if location else None
    message = first.get("msg") or "Данные отсутствуют или имеют неверный формат"
    return JSONResponse(
        status_code=422,
        content=error_payload("validation_error", message, field),
    )


@app.exception_handler(StarletteHTTPException)
async def handle_http_error(
    request: Request, exc: StarletteHTTPException
) -> JSONResponse:
    code = STATUS_CODE_MAP.get(exc.status_code, "http_error")
    message = exc.detail if isinstance(exc.detail, str) else "Ошибка запроса"
    return JSONResponse(
        status_code=exc.status_code,
        content=error_payload(code, message),
        headers=getattr(exc, "headers", None),
    )


app.include_router(api_router, prefix=settings.api_v1_prefix)


@app.get("/health", tags=["service"], summary="Проверка доступности сервиса")
async def health() -> dict[str, str]:
    return {"status": "ok"}


# Раздача frontend тем же сервером: http://127.0.0.1:8000 откроет index.html.
# Монтируется последним, чтобы не перекрывать /api, /docs и /health.
_frontend_path = Path(settings.frontend_dir)
if _frontend_path.is_dir():
    app.mount(
        "/",
        StaticFiles(directory=str(_frontend_path), html=True),
        name="frontend",
    )
