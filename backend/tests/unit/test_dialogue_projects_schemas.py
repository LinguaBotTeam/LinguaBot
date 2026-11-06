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
