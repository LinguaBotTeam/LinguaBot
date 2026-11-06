# API авторизации и теста уровня

Контракт для подключения frontend к backend. Базовый префикс — `/api/v1`, формат — JSON. Защищённые запросы отправляют заголовок `Authorization: Bearer <access_token>`.

Готовые вызовы уже есть в `frontend/src/api/client.js`: `register`, `login`, `me`, `getQuestions`, `submitTest`, `getResult`, `getToken`, `getStoredUser`, `saveSession`, `clearSession`.

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

## Тест уровня

Все запросы требуют Bearer-токен.

| Метод и путь | Тело запроса | Успешный ответ |
| --- | --- | --- |
| `GET /assessment/questions` | — | 200, `QuestionsResponse` |
| `POST /assessment/submit` | `answers` | 201, `TestResultRead` |
| `GET /assessment/result` | — | 200, `TestResultRead` |

`QuestionsResponse` — правильные ответы не отдаются:

```json
{
  "language": "en",
  "questions": [
    {
      "id": 1,
      "text": "She ___ to work by bus every day.",
      "options": [
        {"id": 1, "text": "go"},
        {"id": 2, "text": "goes"},
        {"id": 3, "text": "going"},
        {"id": 4, "text": "gone"}
      ]
    }
  ]
}
```

`POST /assessment/submit`:

```json
{
  "answers": [
    {"question_id": 1, "option_id": 2},
    {"question_id": 2, "option_id": 1}
  ]
}
```

`TestResultRead`:

```json
{
  "id": 13,
  "score": 100,
  "level": "advanced",
  "cefr": "C1",
  "language": "en",
  "questions": [
    {"question_id": 1, "correct": true, "correct_option_id": 2}
  ],
  "taken_at": "2026-10-25T11:47:48"
}
```

Правила:

- В `answers` должны быть **все** вопросы теста (сейчас 5), по одному ответу на `question_id`; `option_id` обязан быть из списка вариантов этого вопроса.
- Пустой список → 422 `validation_error` (`field: "answers"`).
- Частичный набор, повтор вопроса, неизвестный вопрос или чужой `option_id` → 422 `invalid_answers`.
- `score` — процент правильных ответов: `round(correct / 5 * 100)`.
- В ответе на отправку приходит `correct_option_id` — его можно использовать для разбора. В вопросах этого поля нет.

Соответствие результата:

| `score` | `level` | `cefr` |
| --- | --- | --- |
| 0–20 | `beginner` | A1 |
| 40 | `beginner` | A2 |
| 60 | `intermediate` | B1 |
| 80 | `intermediate` | B2 |
| 100 | `advanced` | C1 |

`GET /assessment/result` возвращает последний сохранённый результат или 404 `result_not_found`, если тест ещё не проходился. Для UI это пустое состояние, а не ошибка.

## Общий формат ошибок

```json
{"error": {"code": "invalid_answers", "message": "Ответы должны покрывать все вопросы теста одним вариантом каждый", "field": null}}
```

`field` заполняется для ошибок валидации и указывает, какой input подсветить. Сообщения `validation_error` приходят от Pydantic на английском — для русского интерфейса их нужно замапить по `field` или `code`.

## Замечания для интеграции

- Гость не может открыть тест: `GET /assessment/questions` вернёт 401 `unauthorized`. Перед переходом к тесту проверяйте `LinguaBotAPI.getToken()`, а при 401 очищайте сессию и открывайте модалку входа.
- Сейчас `taken_at` сериализуется без таймзоны. На фронте трактуйте его как UTC (добавьте `Z` перед `new Date(...)`), пока backend не начнёт отдавать ISO-время с зоной.
- `token_type` приходит с заглавной буквы (`Bearer`), но заголовок собирайте как `'Bearer ' + token` — как это уже делает `client.js`.
- Базовый URL по умолчанию — `http://127.0.0.1:8000/api/v1`. Для другого окружения задайте `window.LINGUABOT_API_URL` до подключения `client.js`.
