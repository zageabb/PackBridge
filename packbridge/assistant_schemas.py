from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class AssistantFieldChange(BaseModel):
    model_config = ConfigDict(extra="forbid")

    path: str = Field(min_length=1, max_length=400)
    value: Any = None
    unit: str | None = Field(default=None, max_length=80)
    reason: str = Field(min_length=1, max_length=1200)


class AssistantDataQuery(BaseModel):
    model_config = ConfigDict(extra="forbid")

    operation: Literal[
        "count_packages",
        "filter_packages",
        "sum_package_field",
        "list_modified_fields",
        "list_issues",
    ]
    field: Literal[
        "gross_weight",
        "net_weight",
        "length",
        "width",
        "height",
        "item_count",
    ] | None = None
    comparator: Literal["gt", "gte", "lt", "lte", "eq"] | None = None
    value: float | None = None
    unit: str | None = Field(default=None, max_length=40)
    severity: Literal["INFO", "WARNING", "BLOCKING"] | None = None


class AssistantStructuredReply(BaseModel):
    model_config = ConfigDict(extra="forbid")

    message: str = Field(min_length=1, max_length=10000)
    proposed_changes: list[AssistantFieldChange] = Field(default_factory=list, max_length=10)
    clarification_question: str | None = Field(default=None, max_length=2000)
    data_queries: list[AssistantDataQuery] = Field(default_factory=list, max_length=6)
