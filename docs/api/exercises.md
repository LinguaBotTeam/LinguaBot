# API грамматического упражнения

Один формат упражнения: выбрать верный вариант из четырёх. Сложность
подбирается по последнему результату теста уровня. Правильный ответ и
объяснение не отдаются в запросе задания — только в ответе на проверку.
Все запросы требуют `Authorization: Bearer <access_token>`.

## Маршруты

| Запрос | Тело | Ответ |
| --- | --- | --- |
| `GET /api/v1/exercises/next` | — | 200, `ExerciseRead` |
| `GET /api/v1/exercises/next?exclude=101,102` | — | 200, `ExerciseRead` |
| `POST /api/v1/exercises/{id}/answer` | `{"option_id": 2}` | 200, `AnswerFeedback` |

`ExerciseRead` (без правильного ответа):

```json
{
  "id": 101,
  "difficulty": "beginner",
  "level_source": "test",
  "topic": "Present Simple",
  "prompt": "She ___ to work by bus every day.",
  "options": [
    {"id": 1, "text": "go"},
    {"id": 2, "text": "goes"},
    {"id": 3, "text": "going"},
    {"id": 4, "text": "gone"}
  ]
}
```

`AnswerFeedback`:

```json
{
  "exercise_id": 101,
  "difficulty": "beginner",
  "selected_option_id": 1,
  "correct": false,
  "correct_option_id": 2,
  "correct_text": "goes",
  "explanation": "В Present Simple после he/she/it к глаголу добавляется -s: she goes to work."
}
```

Правила:

- `difficulty` — `beginner`, `intermediate` или `advanced`.
- `level_source` — `test`, если сложность взята из последнего результата
  теста, или `default`, если тест ещё не пройден (тогда `beginner`).
- `exclude` — необязательный список ID через запятую, чтобы не повторять
  уже показанные задания. Если исключены все задания уровня, вернётся первое.
- `explanation` приходит и для верного, и для неверного ответа.
- Ошибки: 401 `unauthorized`, 404 `exercise_not_found`,
  422 `invalid_option` (`field: "option_id"`), 422 `validation_error`.

## Примеры заданий по уровням

| Уровень | Тема | Задание | Верный ответ |
| --- | --- | --- | --- |
| beginner | Present Simple | She ___ to work by bus every day. | goes |
| beginner | Past Simple | Yesterday we ___ to the cinema. | went |
| beginner | Артикль a/an | I have ___ apple every morning. | an |
| intermediate | Present Perfect | I ___ in this city since 2019. | have lived |
| intermediate | First Conditional | If it ___ tomorrow, we will stay at home. | rains |
| intermediate | Степени сравнения | This task is ___ than the previous one. | more difficult |
| advanced | Past Perfect | By the time we arrived, the film ___. | had already started |
| advanced | Passive after modal | The report must ___ by Friday, no exceptions. | be submitted |
| advanced | Third Conditional | Had I known about the delay, I ___ earlier. | would have left |

Полный банк с объяснениями: `backend/src/linguabot/modules/exercises/questions.py`.
