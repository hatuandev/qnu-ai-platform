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
POLICY = 'qnu-compilation-review/v5'
REGISTRY = 'knowledge_compilation_registry'
REVIEW_REASON_MAX_CHARS = 4096  # Bounded diagnostics, independent of evidence/verdict requirements.
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
    resume_from_job_id: str | None = Field(default=None, max_length=100)
    expected_resume_version: int | None = Field(default=None, ge=1)

    @model_validator(mode='after')
    def resume_version(self):
        if (self.resume_from_job_id is None) != (self.expected_resume_version is None):
            raise PydanticCustomError('compilation_resume_version', 'Resume requires a job and its version')
        return self


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
    reason: str = Field(min_length=1, max_length=REVIEW_REASON_MAX_CHARS)


class PacketCheck(CompilationContract):
    items: list[ItemCheck] = Field(default_factory=list, max_length=48)
    missed_evidence_ids: list[str] = Field(default_factory=list, max_length=128)


class PacketCoverage(CompilationContract):
    missed_evidence_ids: list[str] = Field(max_length=128)
    reason: str = Field(min_length=1,max_length=REVIEW_REASON_MAX_CHARS)


class SynthesisDraft(CompilationContract):
    relations: list[CompilationRelation] = Field(default_factory=list, max_length=64)
    sections: list[CompilationSection] = Field(min_length=1, max_length=32)


class CrossRelationDraft(CompilationContract):
    relations: list[CompilationRelation] = Field(default_factory=list, max_length=64)


class CrossRelationCheck(CompilationContract):
    items: list[ItemCheck] = Field(default_factory=list, max_length=64)


class SectionCheck(CompilationContract):
    index: int = Field(ge=0, le=63)
    verdict: Literal['supported', 'unresolved', 'contradicted']
    assertion_ids: list[str] = Field(min_length=1, max_length=24)
    reason: str = Field(min_length=1, max_length=REVIEW_REASON_MAX_CHARS)


class SynthesisCheck(CompilationContract):
    relations: list[ItemCheck] = Field(default_factory=list, max_length=64)
    sections: list[SectionCheck] = Field(min_length=1, max_length=64)


class ManifestSectionCheck(SectionCheck):
    index: int = Field(ge=0)


class ManifestSynthesisCheck(CompilationContract):
    relations: list[ItemCheck] = Field(default_factory=list)
    sections: list[ManifestSectionCheck] = Field(min_length=1)


class DirectedWitness(CompilationContract):
    id: str
    verdict: Literal['supported', 'unresolved', 'contradicted']
    source_id: str | None = None
    target_id: str | None = None
    evidence_ids: list[str] = Field(default_factory=list, max_length=24)
    reason: str = Field(min_length=1, max_length=REVIEW_REASON_MAX_CHARS)


class RelationDirections(CompilationContract):
    items: list[DirectedWitness] = Field(max_length=64)


class ManifestDirections(CompilationContract):
    items: list[DirectedWitness] = Field(default_factory=list)


class CoverageItem(CompilationContract):
    evidence_id: str
    role: Literal['required_assertion', 'supporting_context', 'unrelated', 'unresolved']
    assertion_ids: list[str] = Field(default_factory=list, max_length=48)
    reason: str = Field(min_length=1, max_length=REVIEW_REASON_MAX_CHARS)


class CoverageAudit(CompilationContract):
    items: list[CoverageItem] = Field(max_length=128)

    @model_validator(mode='after')
    def role_binding(self):
        for item in self.items:
            if ((item.role == 'supporting_context' and not item.assertion_ids)
                    or (item.role == 'unrelated' and item.assertion_ids)):
                raise PydanticCustomError('coverage_role_binding',
                    'supporting_context requires offered assertion_ids; unrelated requires assertion_ids=[]')
        return self


class CompilerPolicy(CompilationContract):
    max_calls: int = Field(default=64, ge=4, le=64)
    max_packets: int = Field(default=30, ge=1, le=256)
    max_primary_per_packet: int = Field(default=4, ge=1, le=48,
        description='Output headroom for structured entity/assertion JSON; not a token guarantee or evidence limit.')
    timeout_seconds: int = Field(default=600, ge=10, le=600)
    max_units: int = Field(default=2000, ge=1, le=2000)
    max_total_calls: int = Field(default=64, ge=4, le=512)
    max_output_tokens: int = Field(default=2500, ge=50)
    context_budget_tokens: int = Field(default=24000, ge=1024)
    automatic_output_budget: bool = False
    tokenizer_encoding: Literal['o200k_harmony','o200k_base','cl100k_base'] | None = None
    chat_overhead_tokens: int = Field(0,ge=0)
    max_manifest_objects: int = Field(default=20000, ge=1)
    max_relation_search_pairs: int = Field(default=20000, ge=1)
    token_budget_basis: str = 'conservative_server_fallback_unverified'
    reasoning_effort: Literal['low', 'medium', 'high'] | None = None
    request_timeout_seconds: int = Field(default=30, ge=1, le=600)
