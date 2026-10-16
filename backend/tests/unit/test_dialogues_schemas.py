"""Валидация данных чата до записи в базу."""

import pytest
from pydantic import ValidationError


def test_dialogue_defaults_and_trimmed_title():
    from linguabot.modules.dialogues.schemas import DialogueCreate

    data = DialogueCreate(title="  Разговор в кафе  ")
    assert data.title == "Разговор в кафе"
    assert data.scenario == "free_chat"
    assert DialogueCreate().title == "Новый диалог"


@pytest.mark.parametrize("field,value", [("title", "  "), ("title", "x" * 161), ("scenario", ""), ("scenario", "x" * 65)])
def test_invalid_dialogue_fields_are_rejected(field, value):
    from linguabot.modules.dialogues.schemas import DialogueCreate

    with pytest.raises(ValidationError):
        DialogueCreate(**{field: value})


def test_client_cannot_choose_dialogue_owner():
    from linguabot.modules.dialogues.schemas import DialogueCreate

    with pytest.raises(ValidationError):
        DialogueCreate(user_id=123)


def test_message_is_trimmed_without_changing_internal_text():
    from linguabot.modules.dialogues.schemas import MessageCreate

    assert MessageCreate(content="  Привет!\nКак дела?  ").content == "Привет!\nКак дела?"


@pytest.mark.parametrize("content", ["", " \n\t ", "x" * 4001])
def test_invalid_message_content_is_rejected(content):
    from linguabot.modules.dialogues.schemas import MessageCreate

    with pytest.raises(ValidationError):
        MessageCreate(content=content)


@pytest.mark.parametrize("extra", [{"role": "assistant"}, {"dialogue_id": 99}])
def test_message_metadata_cannot_be_supplied_by_client(extra):
    from linguabot.modules.dialogues.schemas import MessageCreate

    with pytest.raises(ValidationError):
        MessageCreate(content="Привет", **extra)
