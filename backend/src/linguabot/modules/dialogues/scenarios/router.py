"""Read-only scenario menu using the same catalogue as the LLM prompts."""

from fastapi import APIRouter

from linguabot.modules.auth.dependencies import CurrentUser
from linguabot.modules.dialogues.scenarios.catalog import SCENARIOS
from linguabot.modules.dialogues.scenarios.schemas import ScenarioRead

router = APIRouter()


@router.get(
    "", response_model=list[ScenarioRead],
    summary="Список тем для практики английского",
)
async def list_scenarios(current_user: CurrentUser) -> list[ScenarioRead]:
    return [
        ScenarioRead(title=definition.title, scenario=key)
        for key, definition in SCENARIOS.items()
    ]
