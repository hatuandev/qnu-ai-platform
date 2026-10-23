"""Phase-two contracts: untrusted compilation proposals cannot declare approval."""
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator
from pydantic_core import PydanticCustomError

VERSION = 'qnu-knowledge-compilation/v1'


class CompilationContract(BaseModel):
    model_config = ConfigDict(extra='forbid')


class CompilationTime(CompilationContract):
    role: Literal['data', 'publication', 'effective', 'event', 'unknown']
    years: list[int] = Field(default_factory=list, max_length=10)
    evidence_ids: list[str] = Field(default_factory=list, max_length=12)

    @model_validator(mode='after')
    def explicit_scope(self):
        if self.role == 'unknown':
            if self.years or self.evidence_ids:
                raise PydanticCustomError('compilation_unknown_time_requires_empty_scope',
                    'Unknown time requires empty years and evidence_ids')
        elif not self.years or not self.evidence_ids or any(type(y) is not int or not 1900 <= y <= 2099 for y in self.years):
            raise PydanticCustomError('compilation_time_requires_literal_year_and_evidence',
                'A known temporal role requires nonempty literal years and evidence_ids; omit unproved temporal entries')
        return self


class CompilationEntity(CompilationContract):
    id: str = Field(min_length=1, max_length=100)
    label: str = Field(min_length=1, max_length=200)
    evidence_ids: list[str] = Field(min_length=1, max_length=12)


class CompilationScope(CompilationContract):
    dimension: str = Field(min_length=1, max_length=100)
    value: str = Field(min_length=1, max_length=200)
    evidence_ids: list[str] = Field(min_length=1, max_length=12)


class CompilationAssertion(CompilationContract):
    id: str = Field(min_length=1, max_length=100)
    entity_id: str
    attribute: str = Field(min_length=1, max_length=200)
    value: str | None = Field(default=None, max_length=2000)
    value_state: Literal['present', 'unknown', 'conflict']
    unit: str | None = Field(default=None, max_length=100)
    evidence_ids: list[str] = Field(min_length=1, max_length=12)
    temporal: list[CompilationTime] = Field(default_factory=list, max_length=8)
    scope: list[CompilationScope] = Field(default_factory=list, max_length=12)
    condition_ids: list[str] = Field(default_factory=list, max_length=12)
    exception_ids: list[str] = Field(default_factory=list, max_length=12)

    @model_validator(mode='after')
    def unknown_is_not_zero(self):
        if (self.value_state == 'present') != bool(self.value is not None and self.value.strip()):
            if self.value_state == 'present':
                raise PydanticCustomError('compilation_present_requires_scalar',
                    'A present value requires a nonempty scalar; use unknown/null only when proved by the source')
            raise PydanticCustomError('compilation_unresolved_cannot_hold_scalar',
                'Unknown/conflict cannot hold a nonempty scalar; use value=null and retain unresolved literals in evidence')
        return self


class CompilationRelation(CompilationContract):
    id: str = Field(min_length=1, max_length=100)
    source_id: str
    target_id: str
    kind: Literal['same_entity', 'alias', 'supports', 'contradicts', 'supersedes', 'prerequisite', 'exception']
    evidence_ids: list[str] = Field(min_length=1, max_length=12)
    temporal: list[CompilationTime] = Field(default_factory=list, max_length=8)
    scope: list[CompilationScope] = Field(default_factory=list, max_length=12)
    condition_ids: list[str] = Field(default_factory=list, max_length=12)
    exception_ids: list[str] = Field(default_factory=list, max_length=12)


class CompilationSection(CompilationContract):
    heading: str = Field(min_length=1, max_length=200)
    text: str = Field(min_length=1, max_length=3000)
    assertion_ids: list[str] = Field(min_length=1, max_length=24)


class CompilationDraft(CompilationContract):
    version: Literal['qnu-knowledge-compilation/v1'] = VERSION
    snapshot_hash: str = Field(pattern=r'^[a-f0-9]{64}$')
    entities: list[CompilationEntity] = Field(min_length=1, max_length=64)
    assertions: list[CompilationAssertion] = Field(min_length=1, max_length=128)
    relations: list[CompilationRelation] = Field(default_factory=list, max_length=128)
    sections: list[CompilationSection] = Field(default_factory=list, max_length=64)
