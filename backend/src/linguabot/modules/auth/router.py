"""Маршруты аутентификации."""

from fastapi import APIRouter, status

from linguabot.core.errors import APIError
from linguabot.modules.auth import service
from linguabot.modules.auth.dependencies import CurrentUser, SessionDep
from linguabot.modules.auth.schemas import LoginRequest, LoginResponse, RegisterRequest
from linguabot.modules.users.schemas import UserRead

router = APIRouter()


@router.post(
    "/register",
    response_model=UserRead,
    status_code=status.HTTP_201_CREATED,
    summary="Регистрация нового пользователя",
)
async def register(data: RegisterRequest, session: SessionDep) -> UserRead:
    """Создаёт аккаунт и возвращает объект пользователя (без пароля и токена)."""
    try:
        return await service.register_user(session, data)
    except service.EmailAlreadyRegisteredError:
        raise APIError(
            status_code=409,
            code="email_taken",
            message="Пользователь с таким email уже зарегистрирован",
        ) from None


@router.post("/login", response_model=LoginResponse, summary="Вход по email и паролю")
async def login(data: LoginRequest, session: SessionDep) -> LoginResponse:
    """Проверяет email и пароль, возвращает JWT и объект пользователя."""
    try:
        user = await service.authenticate_user(session, data)
    except service.InvalidCredentialsError:
        raise APIError(
            status_code=401,
            code="invalid_credentials",
            message="Неверный email или пароль",
        ) from None
    return service.build_login_response(user)


@router.get("/me", response_model=UserRead, summary="Текущий пользователь")
async def me(current_user: CurrentUser) -> UserRead:
    return current_user
