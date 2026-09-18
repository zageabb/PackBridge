from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class LearnedFieldAlias(BaseModel):
    model_config = ConfigDict(extra="forbid")

    source_term: str = Field(min_length=1, max_length=160)
    canonical_field: str = Field(min_length=1, max_length=300)
    note: str | None = Field(default=None, max_length=500)


class LearnedProfileDraft(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str = Field(min_length=1, max_length=200)
    vendor_name: str = Field(min_length=1, max_length=200)
    document_type: str = Field(default="packing_list", max_length=80)
    recognition_indicators: list[str] = Field(default_factory=list, max_length=20)
    field_aliases: list[LearnedFieldAlias] = Field(default_factory=list, max_length=60)
    continuation_key: str | None = Field(default=None, max_length=300)
    interpretation_notes: list[str] = Field(default_factory=list, max_length=20)
