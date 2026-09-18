from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class AssistantFieldChange(BaseModel):
    model_config = ConfigDict(extra="forbid")

    path: str = Field(min_length=1, max_length=400)
    value: Any = None
    unit: str | None = Field(default=None, max_length=80)
    reason: str = Field(min_length=1, max_length=1200)


class AssistantStructuredReply(BaseModel):
    model_config = ConfigDict(extra="forbid")

    message: str = Field(min_length=1, max_length=10000)
    proposed_changes: list[AssistantFieldChange] = Field(default_factory=list, max_length=10)
    clarification_question: str | None = Field(default=None, max_length=2000)
