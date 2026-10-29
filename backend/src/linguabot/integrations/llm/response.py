"""Private English generation contract; public feedback is rendered separately."""

from pydantic import BaseModel, ConfigDict, Field


class OllamaReply(BaseModel):
    model_config = ConfigDict(strict=True, extra="forbid", str_strip_whitespace=True)

    reply: str = Field(min_length=1, max_length=4000)
    corrected_text: str | None = Field(min_length=1, max_length=4000)
