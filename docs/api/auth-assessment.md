# API авторизации

Контракт для подключения frontend к backend. Базовый префикс — `/api/v1`, формат — JSON. Защищённые запросы отправляют заголовок `Authorization: Bearer <access_token>`.

Готовые вызовы уже есть в `frontend/src/api/client.js`: `register`, `login`, `me`, `getToken`, `getStoredUser`, `saveSession`, `clearSession`.

## Авторизация

| Метод и путь | Auth | Тело запроса | Успешный ответ |
| --- | --- | --- | --- |
| `POST /auth/register` | нет | `name`, `email`, `password` | 201, `UserRead` |
| `POST /auth/login` | нет | `email`, `password` | 200, `LoginResponse` |
| `GET /auth/me` | Bearer | — | 200, `UserRead` |

`UserRead`:

```json
{"id": 1, "name": "Иван", "email": "ivan@example.com"}
```

`LoginResponse`:

```json
{
  "access_token": "eyJhbGciOi...",
  "token_type": "Bearer",
  "expires_in": 604800,
  "user": {"id": 1, "name": "Иван", "email": "ivan@example.com"}
}
```

Правила:

- `name` — 2–120 символов, `password` — 8–128, `email` — валидный адрес.
- Email приводится к нижнему регистру, внешние пробелы удаляются.
- Регистрация **не возвращает токен**: после 201 нужно выполнить вход.
- `expires_in` — срок жизни токена в секундах (по умолчанию 7 дней). Фронт может его сохранить, но при истечении `GET /auth/me` вернёт 401.

Ошибки:

| Статус | `code` | Когда |
| --- | --- | --- |
| 401 | `invalid_credentials` | Неверная пара email/пароль |
| 401 | `unauthorized` | Нет токена, он истёк или пользователь не найден |
| 409 | `email_taken` | Email уже зарегистрирован |
| 422 | `validation_error` | Неверный формат полей, в `field` — имя поля |
