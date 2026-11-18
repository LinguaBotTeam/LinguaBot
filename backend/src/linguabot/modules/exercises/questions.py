"""Банк грамматических упражнений по трём уровням сложности.

Один формат: выбрать верный вариант из четырёх. Правильный ответ и
объяснение хранятся на сервере и не отдаются до проверки ответа.
"""

DIFFICULTIES = ("beginner", "intermediate", "advanced")

EXERCISES: dict[str, list[dict]] = {
    "beginner": [
        {
            "id": 101,
            "topic": "Present Simple",
            "prompt": "She ___ to work by bus every day.",
            "options": [
                {"id": 1, "text": "go"},
                {"id": 2, "text": "goes"},
                {"id": 3, "text": "going"},
                {"id": 4, "text": "gone"},
            ],
            "correct_option_id": 2,
            "explanation": (
                "В Present Simple после he/she/it к глаголу добавляется -s: "
                "she goes to work."
            ),
        },
        {
            "id": 102,
            "topic": "Past Simple",
            "prompt": "Yesterday we ___ to the cinema.",
            "options": [
                {"id": 1, "text": "go"},
                {"id": 2, "text": "goes"},
                {"id": 3, "text": "went"},
                {"id": 4, "text": "gone"},
            ],
            "correct_option_id": 3,
            "explanation": (
                "Слово yesterday указывает на Past Simple, поэтому нужна "
                "форма went."
            ),
        },
        {
            "id": 103,
            "topic": "Артикль a/an",
            "prompt": "I have ___ apple every morning.",
            "options": [
                {"id": 1, "text": "a"},
                {"id": 2, "text": "an"},
                {"id": 3, "text": "the"},
                {"id": 4, "text": "—"},
            ],
            "correct_option_id": 2,
            "explanation": (
                "Перед словом, которое начинается с гласного звука, "
                "употребляется an: an apple."
            ),
        },
    ],
    "intermediate": [
        {
            "id": 201,
            "topic": "Present Perfect",
            "prompt": "I ___ in this city since 2019.",
            "options": [
                {"id": 1, "text": "live"},
                {"id": 2, "text": "lived"},
                {"id": 3, "text": "have lived"},
                {"id": 4, "text": "am living"},
            ],
            "correct_option_id": 3,
            "explanation": (
                "С since описывается период до настоящего момента, поэтому "
                "нужен Present Perfect: I have lived."
            ),
        },
        {
            "id": 202,
            "topic": "First Conditional",
            "prompt": "If it ___ tomorrow, we will stay at home.",
            "options": [
                {"id": 1, "text": "rains"},
                {"id": 2, "text": "will rain"},
                {"id": 3, "text": "would rain"},
                {"id": 4, "text": "rained"},
            ],
            "correct_option_id": 1,
            "explanation": (
                "В условном предложении первого типа после if используется "
                "Present Simple, а will — только в главной части."
            ),
        },
        {
            "id": 203,
            "topic": "Степени сравнения",
            "prompt": "This task is ___ than the previous one.",
            "options": [
                {"id": 1, "text": "more difficult"},
                {"id": 2, "text": "difficultest"},
                {"id": 3, "text": "the most difficult"},
                {"id": 4, "text": "most difficult"},
            ],
            "correct_option_id": 1,
            "explanation": (
                "Многосложные прилагательные образуют сравнение через "
                "more + прилагательное + than: more difficult than."
            ),
        },
    ],
    "advanced": [
        {
            "id": 301,
            "topic": "Past Perfect",
            "prompt": "By the time we arrived, the film ___.",
            "options": [
                {"id": 1, "text": "already started"},
                {"id": 2, "text": "has already started"},
                {"id": 3, "text": "had already started"},
                {"id": 4, "text": "was already starting"},
            ],
            "correct_option_id": 3,
            "explanation": (
                "Past Perfect обозначает действие, завершившееся до другого "
                "действия в прошлом: the film had already started before we "
                "arrived."
            ),
        },
        {
            "id": 302,
            "topic": "Passive after modal",
            "prompt": "The report must ___ by Friday, no exceptions.",
            "options": [
                {"id": 1, "text": "be submitted"},
                {"id": 2, "text": "submit"},
                {"id": 3, "text": "be submitting"},
                {"id": 4, "text": "have submitted"},
            ],
            "correct_option_id": 1,
            "explanation": (
                "После модального must пассив образуется как must be + "
                "Past Participle: must be submitted."
            ),
        },
        {
            "id": 303,
            "topic": "Third Conditional",
            "prompt": "Had I known about the delay, I ___ earlier.",
            "options": [
                {"id": 1, "text": "would leave"},
                {"id": 2, "text": "would have left"},
                {"id": 3, "text": "had left"},
                {"id": 4, "text": "will leave"},
            ],
            "correct_option_id": 2,
            "explanation": (
                "Конструкция Had I known — инверсия третьего условного: "
                "в главной части будет would have left."
            ),
        },
    ],
}

EXERCISES_BY_ID: dict[int, dict] = {
    exercise["id"]: {**exercise, "difficulty": difficulty}
    for difficulty, items in EXERCISES.items()
    for exercise in items
}
