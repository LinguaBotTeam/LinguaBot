"""Server-owned topics; stored scenario text is never an instruction."""

from linguabot.modules.dialogues.scenarios.catalog import SCENARIOS

_FREE_CHAT = (
    "Have a friendly everyday English conversation about a safe topic "
    "chosen by the learner."
)


def scenario_instructions(scenario: str) -> str:
    definition = SCENARIOS.get(scenario.strip().lower())
    if definition is None:
        return _FREE_CHAT
    steps = "\n".join(
        f"{number}. {step}"
        for number, step in enumerate(definition.steps, start=1)
    )
    return (
        f"Bot role: {definition.bot_role}\n"
        f"Learner goal: {definition.learner_goal}\n"
        f"Guiding steps:\n{steps}"
    )
