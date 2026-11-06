"""Project input normalization and ownership must stay server-controlled."""

import pytest
from pydantic import ValidationError


@pytest.mark.parametrize("name,expected", [
    ("  Trip  ", "Trip"), ("x", "x"), ("x" * 160, "x" * 160),
])
def test_project_name_is_trimmed_and_bounded(name, expected):
    from linguabot.modules.dialogues.projects.schemas import ProjectCreate

    assert ProjectCreate(name=name).name == expected


@pytest.mark.parametrize("payload", [
    {}, {"name": ""}, {"name": "   "}, {"name": "x" * 161},
    {"name": "Trip", "user_id": 1}, {"name": "Trip", "extra": True},
])
def test_invalid_project_input_is_rejected(payload):
    from linguabot.modules.dialogues.projects.schemas import ProjectCreate

    with pytest.raises(ValidationError):
        ProjectCreate.model_validate(payload)


@pytest.mark.parametrize("project_id", [None, 1, 2147483647])
def test_project_assignment_accepts_id_or_explicit_null(project_id):
    from linguabot.modules.dialogues.schemas import (
        DialogueCreate, DialogueProjectChange,
    )

    assert DialogueCreate(project_id=project_id).project_id == project_id
    assert DialogueProjectChange(
        project_id=project_id).project_id == project_id
    assert DialogueCreate().project_id is None


@pytest.mark.parametrize("payload", [
    {}, {"project_id": 0}, {"project_id": -1},
    {"project_id": 2147483648}, {"project_id": "invalid"},
    {"project_id": 1, "user_id": 123},
])
def test_invalid_assignment_is_rejected(payload):
    from pydantic import ValidationError
    from linguabot.modules.dialogues.schemas import DialogueProjectChange

    with pytest.raises(ValidationError):
        DialogueProjectChange(**payload)
