"""Public menu entries for the supported English dialogue topics."""

from pydantic import BaseModel


class ScenarioRead(BaseModel):
    title: str
    scenario: str
