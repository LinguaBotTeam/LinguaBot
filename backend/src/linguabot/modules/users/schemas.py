"""Pydantic-схемы пользователя."""

from pydantic import BaseModel, ConfigDict, EmailStr


class UserRead(BaseModel):
    """Пользователь в ответах API: id, name, email (пароль не включается)."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    email: EmailStr
