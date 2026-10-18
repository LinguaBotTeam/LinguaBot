"""Фиксированный банк вопросов теста уровня (пока только английский).

Правильные ответы хранятся здесь и не отдаются клиенту до отправки теста.
"""

ENGLISH_QUESTIONS: list[dict] = [
    {
        "id": 1,
        "text": "She ___ to work by bus every day.",
        "options": [
            {"id": 1, "text": "go"},
            {"id": 2, "text": "goes"},
            {"id": 3, "text": "going"},
            {"id": 4, "text": "gone"},
        ],
        "correct_option_id": 2,
    },
    {
        "id": 2,
        "text": "Yesterday I ___ a very interesting book.",
        "options": [
            {"id": 1, "text": "read"},
            {"id": 2, "text": "reads"},
            {"id": 3, "text": "was reading"},
            {"id": 4, "text": "have read"},
        ],
        "correct_option_id": 1,
    },
    {
        "id": 3,
        "text": "If it ___ tomorrow, we will stay at home.",
        "options": [
            {"id": 1, "text": "rains"},
            {"id": 2, "text": "will rain"},
            {"id": 3, "text": "would rain"},
            {"id": 4, "text": "rained"},
        ],
        "correct_option_id": 1,
    },
    {
        "id": 4,
        "text": "By the time we arrived, the film ___.",
        "options": [
            {"id": 1, "text": "already started"},
            {"id": 2, "text": "has already started"},
            {"id": 3, "text": "had already started"},
            {"id": 4, "text": "was already starting"},
        ],
        "correct_option_id": 3,
    },
    {
        "id": 5,
        "text": "The report must ___ by Friday, no exceptions.",
        "options": [
            {"id": 1, "text": "be submitted"},
            {"id": 2, "text": "submit"},
            {"id": 3, "text": "be submitting"},
            {"id": 4, "text": "have submitted"},
        ],
        "correct_option_id": 1,
    },
]

QUESTION_COUNT = len(ENGLISH_QUESTIONS)

QUESTIONS_BY_ID = {question["id"]: question for question in ENGLISH_QUESTIONS}
