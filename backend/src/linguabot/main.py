"""Точка входа приложения FastAPI."""

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, RedirectResponse
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


# Старые отдельные страницы входа и регистрации убраны в пользу модального окна.
# Ссылки и закладки на них ведут на главную и открывают нужную форму.
@app.get("/login.html", include_in_schema=False)
async def legacy_login() -> RedirectResponse:
    return RedirectResponse(url="/?auth=login", status_code=307)


@app.get("/register.html", include_in_schema=False)
async def legacy_register() -> RedirectResponse:
    return RedirectResponse(url="/?auth=register", status_code=307)


# Раздача frontend тем же сервером: http://127.0.0.1:8000 откроет index.html.
# Монтируется последним, чтобы не перекрывать /api, /docs и /health.
class NoCacheStaticFiles(StaticFiles):
    """Статика без агрессивного кеша, чтобы браузер не показывал старые файлы."""

    async def get_response(self, path: str, scope) -> object:
        response = await super().get_response(path, scope)
        response.headers["Cache-Control"] = "no-cache"
        return response


_frontend_path = Path(settings.frontend_dir)
if _frontend_path.is_dir():
    app.mount(
        "/",
        NoCacheStaticFiles(directory=str(_frontend_path), html=True),
        name="frontend",
    )
