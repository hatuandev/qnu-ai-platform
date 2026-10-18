"""Explicit administrator approval; review identity never comes from the client."""

from typing import Literal

from pydantic import Field, field_validator

from app.modules.rag.evidence_schemas import StrictContract
from app.modules.rag.score_conversion_schemas import ConversionDefinition


class VersionedCommand(StrictContract):
    expected_version: int = Field(ge=0, strict=True)
    request_id: str = Field(min_length=8, max_length=100)


class RuleDraft(VersionedCommand):
    definition: ConversionDefinition


class RuleImport(VersionedCommand):
    definitions: list[ConversionDefinition] = Field(min_length=1, max_length=25)


class RuleAction(VersionedCommand):
    action: Literal["approve", "activate", "deactivate", "revoke"]
    confirmed: bool = Field(strict=True)
    reason: str = Field(min_length=3, max_length=500, pattern=r"\S")

    @field_validator("confirmed")
    @classmethod
    def require_confirmation(cls, value: bool) -> bool:
        if not value:
            raise ValueError("Explicit confirmation is required")
        return value

    @field_validator("reason")
    @classmethod
    def meaningful_reason(cls, value: str) -> str:
        if len(value.strip()) < 3:
            raise ValueError("A meaningful review reason is required")
        return value.strip()


class RulePreview(StrictContract):
    expected_version: int = Field(ge=0)
    combination: str = Field(min_length=1, max_length=80)
    score: str = Field(min_length=1, max_length=12)


class RuleRecord(StrictContract):
    definition: ConversionDefinition
    status: Literal["draft", "approved", "active", "revoked"] = "draft"
    created_by: str
    created_at: str
    reviewed_by: str | None = None
    reviewed_at: str | None = None


class RuleAudit(StrictContract):
    rule_id: str
    action: str
    actor_id: str
    at: str
    reason: str
    request_id: str
    command_hash: str


class RuleRegistry(StrictContract):
    version: int = 0
    items: list[RuleRecord] = Field(default_factory=list)
    audit: list[RuleAudit] = Field(default_factory=list)
