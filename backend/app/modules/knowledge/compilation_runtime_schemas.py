"""Bounded compiler requests and independent checks; no model-owned decisions."""
from typing import Literal

from pydantic import Field, model_validator
from pydantic_core import PydanticCustomError

from app.modules.knowledge.compilation_schemas import (
    CompilationAssertion,
    CompilationContract,
    CompilationEntity,
    CompilationRelation,
    CompilationSection,
)

COMPILER = 'qnu-topic-compiler/v1'
POLICY = 'qnu-compilation-review/v3'
REGISTRY = 'knowledge_compilation_registry'
TEMPORAL_ROLES = {
    'data': 'Period that the reported metric describes; not a file name or document dateline.',
    'publication': 'Explicitly stated publication or issuance date; a version date alone does not prove publication.',
    'effective': 'Explicitly stated start/end of legal validity or applicability.',
    'event': 'Reported occurrence, including a source version/revision/update event; retain the event kind in the assertion attribute.',
    'unknown': 'Omit unproved time, or use empty years/evidence_ids. Never infer a role just from a date literal.',
}


class CompilationRequest(CompilationContract):
    topic: str = Field(min_length=3, max_length=200)
    source_revision_ids: list[str] = Field(min_length=1, max_length=16)
    expected_source_set_hash: str = Field(pattern=r'^[a-f0-9]{64}$')
    idempotency_key: str = Field(pattern=r'^[a-zA-Z0-9_-]{8,100}$')


class CompilationAction(CompilationContract):
    expected_version: int = Field(ge=1)
    expected_proposal_hash: str = Field(pattern=r'^[a-f0-9]{64}$')
    idempotency_key: str = Field(pattern=r'^[a-zA-Z0-9_-]{8,100}$')
    decision: Literal['approved', 'rejected', 'revoked']
    comment: str = Field(default='', max_length=1000)


class PacketDraft(CompilationContract):
    entities: list[CompilationEntity] = Field(default_factory=list, max_length=32,
        description='Local entity objects required for every assertion, including unknown/null assertions.')
    assertions: list[CompilationAssertion] = Field(default_factory=list, max_length=48)
    deferred_evidence_ids: list[str] = Field(default_factory=list, max_length=128)

    @model_validator(mode='after')
    def local_entity_graph(self):
        entities=[entity.id for entity in self.entities]
        assertions=[assertion.id for assertion in self.assertions]
        if len(entities)!=len(set(entities)) or len(assertions)!=len(set(assertions)):
            raise PydanticCustomError('compilation_packet_duplicate_id','Local entity and assertion IDs must be unique within each category')
        if any(assertion.entity_id not in entities for assertion in self.assertions):
            raise PydanticCustomError('compilation_packet_entity_missing',
                'Every assertion.entity_id must match an entity.id in entities; include entity objects for unknown values too')
        if self.entities and not self.assertions:
            raise PydanticCustomError('compilation_packet_orphan_entity','Do not return entities without assertions')
        return self


class TopicSelection(CompilationContract):
    relevant_evidence_ids: list[str] = Field(default_factory=list, max_length=128)
    unrelated_evidence_ids: list[str] = Field(default_factory=list, max_length=128)


class ItemCheck(CompilationContract):
    id: str = Field(min_length=1, max_length=100)
    verdict: Literal['supported', 'unresolved', 'contradicted']
    entity_scope: bool
    temporal_roles: bool
    conditions_complete: bool
    evidence_ids: list[str] = Field(min_length=1, max_length=24)
    reason: str = Field(min_length=1, max_length=400)


class PacketCheck(CompilationContract):
    items: list[ItemCheck] = Field(default_factory=list, max_length=48)
    missed_evidence_ids: list[str] = Field(default_factory=list, max_length=128)


class SynthesisDraft(CompilationContract):
    relations: list[CompilationRelation] = Field(default_factory=list, max_length=64)
    sections: list[CompilationSection] = Field(min_length=1, max_length=32)


class SectionCheck(CompilationContract):
    index: int = Field(ge=0, le=63)
    verdict: Literal['supported', 'unresolved', 'contradicted']
    assertion_ids: list[str] = Field(min_length=1, max_length=24)
    reason: str = Field(min_length=1, max_length=400)


class SynthesisCheck(CompilationContract):
    relations: list[ItemCheck] = Field(default_factory=list, max_length=64)
    sections: list[SectionCheck] = Field(min_length=1, max_length=64)


class DirectedWitness(CompilationContract):
    id: str
    verdict: Literal['supported', 'unresolved', 'contradicted']
    source_id: str | None = None
    target_id: str | None = None
    evidence_ids: list[str] = Field(default_factory=list, max_length=24)
    reason: str = Field(min_length=1, max_length=400)


class RelationDirections(CompilationContract):
    items: list[DirectedWitness] = Field(max_length=64)


class CoverageItem(CompilationContract):
    evidence_id: str
    role: Literal['required_assertion', 'supporting_context', 'unrelated', 'unresolved']
    assertion_ids: list[str] = Field(default_factory=list, max_length=48)
    reason: str = Field(min_length=1, max_length=400)


class CoverageAudit(CompilationContract):
    items: list[CoverageItem] = Field(max_length=128)


class CompilerPolicy(CompilationContract):
    max_calls: int = Field(default=64, ge=4, le=64)
    max_packets: int = Field(default=30, ge=1, le=30)
    max_primary_per_packet: int = Field(default=4, ge=1, le=48,
        description='Output headroom for structured entity/assertion JSON; not a token guarantee or evidence limit.')
    timeout_seconds: int = Field(default=600, ge=10, le=600)
    max_units: int = Field(default=2000, ge=1, le=2000)
