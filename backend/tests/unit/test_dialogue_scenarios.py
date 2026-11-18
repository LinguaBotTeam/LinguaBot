"""Trusted catalogue content and backwards-compatible topic selection."""

import pytest

from linguabot.modules.dialogues.scenarios import scenario_instructions


@pytest.mark.parametrize(
    "key,role,goal,step",
    [
        ("introductions", "language club", "introduce", "country"),
        ("cafe", "barista", "order", "bill"),
        ("shop", "shop assistant", "return", "fitting room"),
        ("travel", "check-in", "connecting", "aisle"),
        ("business_meeting", "business partner", "proposal", "budget"),
        ("doctor_visit", "general practitioner", "symptoms", "allergies"),
        ("renting_a_flat", "landlord", "negotiate", "deposit"),
        ("customer_support", "support agent", "escalation", "refund"),
        ("job_interview", "HR interviewer", "experience", "strength"),
        ("weekend_small_talk", "acquaintance", "invitation", "exhibition"),
    ],
)
def test_topic_instructions_include_role_goal_and_guiding_steps(
    key, role, goal, step,
):
    instructions = scenario_instructions(key)

    assert role in instructions
    assert goal in instructions
    assert step in instructions
    assert "Learner goal:" in instructions
    assert "Guiding steps:" in instructions
    assert all(f"{number}. " in instructions for number in range(1, 6))


@pytest.mark.parametrize("key", ["introductions", "cafe", "shop", "travel"])
def test_topic_selection_still_normalizes_whitespace_and_case(key):
    assert scenario_instructions(f"  {key.upper()}  ") == (
        scenario_instructions(key)
    )


@pytest.mark.parametrize("key", ["free_chat", "", "  ", "SECRET_OVERRIDE"])
def test_unknown_topic_uses_safe_free_chat_fallback(key):
    instructions = scenario_instructions(key)

    assert instructions == scenario_instructions("free_chat")
    assert "friendly everyday English conversation" in instructions
    assert "SECRET_OVERRIDE" not in instructions
