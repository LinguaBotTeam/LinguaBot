# Материалы проверки грамматического упражнения

Задача: одно упражнение по грамматике с тремя уровнями сложности,
автоподбором сложности по тесту и мгновенной обратной связью.

## Файлы экрана и логики

- Экран: `frontend/exercise.html`.
- Логика экрана: `frontend/src/app/exercise.js`.
- Стили: `frontend/src/styles/exercise.css`.
- API-клиент: `frontend/src/api/client.js` (`getNextExercise`, `submitExerciseAnswer`).
- Backend: `backend/src/linguabot/modules/exercises/`
  - `questions.py` — банк заданий и объяснений по трём уровням;
  - `service.py` — выбор сложности по результату теста и проверка ответа;
  - `schemas.py` — контракт запросов и ответов;
  - `router.py` — `GET /exercises/next`, `POST /exercises/{id}/answer`.
- Контракт и примеры заданий: `docs/api/exercises.md`.

## Скриншоты обратной связи

| Уровень | Верный ответ | Неверный ответ |
| --- | --- | --- |
| Начальный | `exercise-beginner-correct.png` | `exercise-beginner-wrong.png` |
| Средний | `exercise-intermediate-correct.png` | `exercise-intermediate-wrong.png` |
| Продвинутый | `exercise-advanced-correct.png` | `exercise-advanced-wrong.png` |

Полная запись сценария: `exercise-flow.webm`.
Черновик Playwright-сценария: `exercise.e2e.spec.js` (не подключён к CI).

## Результат проверки

- `pytest -o pythonpath=src tests/integration/test_exercises.py` — 11 passed.
- Полный backend-набор — 333 passed.
- Playwright-сценарий: по три уровня, верный и неверный ответ — 1 passed.

## Как воспроизвести

1. Запустить backend из `backend` (`PYTHONPATH=src`, `alembic upgrade head`, `uvicorn`).
2. Открыть `http://127.0.0.1:8000/assessment.html`, пройти тест и войти.
3. Перейти по ссылке «Упражнение» или открыть `http://127.0.0.1:8000/exercise.html`.
4. Выбрать вариант и нажать «Проверить» — сразу появятся вердикт и объяснение.

Сложность берётся из последнего результата теста: `beginner`, `intermediate`
или `advanced`. Без пройденного теста показывается начальный уровень.
После ответа доступно «Следующее задание», уже показанные задания не повторяются,
пока не закончится банк уровня.
