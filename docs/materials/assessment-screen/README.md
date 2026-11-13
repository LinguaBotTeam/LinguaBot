# Материалы проверки экрана теста уровня

Задача: PR #6 `feat(frontend): экран теста уровня`.

## Файлы

- `result.png` — скриншот сохранённого результата теста.
- `assessment.e2e.spec.js` — черновик Playwright-сценария: регистрация → тест → результат → reload → выход → повторный вход.
- `assessment-mobile.e2e.spec.js` — проверка мобильной ширины 390 px.

## Как воспроизвести

1. Запустить backend из каталога `backend`:

   ```powershell
   $env:PYTHONPATH = "src"
   .\.venv\Scripts\python.exe -m alembic upgrade head
   .\.venv\Scripts\python.exe -m uvicorn linguabot.main:app --app-dir src --reload
   ```

   `PYTHONPATH=src` обязателен для Alembic, если пакет `linguabot` не установлен в venv: иначе команда падает с `ModuleNotFoundError`.

2. Установить Playwright и браузер в отдельном каталоге, затем скопировать сценарии.
3. Запустить сценарии из каталога с `playwright.config.js`, где `baseURL` равен `http://127.0.0.1:8000`.

## Результат проверки

- `pytest -o pythonpath=src tests/integration/test_assessment.py` — 11 passed (запускалось с `PYTHONPATH=src`).
- Браузерный сценарий входа, теста, сохранения результата и повторного входа — passed.
- Мобильный вид 390 px без горизонтальной прокрутки — passed.
- `node --check` для JS-файлов экрана — без ошибок.

Сценарии являются черновиками и не подключены к CI: они запускались локально после ревью PR #6.
