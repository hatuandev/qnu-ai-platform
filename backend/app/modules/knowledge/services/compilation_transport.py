"""Request-local proof handles; durable revision/hash catalog never comes from the model."""
from typing import Literal

from pydantic import Field, create_model

from app.modules.knowledge.compilation_runtime_schemas import (
    CoverageAudit,
    CoverageItem,
    PacketCheck,
    PacketDraft,
    RelationDirections,
    SynthesisCheck,
    SynthesisDraft,
    TopicSelection,
)
from app.modules.knowledge.compilation_schemas import (
    CompilationAssertion,
    CompilationEntity,
    CompilationRelation,
    CompilationScope,
    CompilationSection,
    CompilationTime,
)

VALUE_STATE_CONTRACT = 'source-unspecified-wire-alias/v1'
TRANSPORT_NOTE = """\nProof IDs u0/u1 and object IDs claim0/ent0/rel0 are opaque request-local handles, never source text; copy offered handles exactly. Output JSON data only.
For assertion.value_state use present, source_unspecified or conflict. source_unspecified means the SOURCE does not specify the requested value: value=null, with evidence proving that limitation.
This is separate from a review verdict: supported means the assertion is proved (including a correctly scoped source limitation); unresolved means the assertion itself lacks sufficient evidence.
Do not use unknown or unresolved as assertion.value_state. Temporal role unknown remains a separate valid role with empty years/evidence_ids."""

REFERENCE_FIELDS = {'evidence_ids', 'condition_ids', 'exception_ids', 'deferred_evidence_ids',
    'relevant_evidence_ids', 'unrelated_evidence_ids', 'primary_evidence_ids', 'missed_evidence_ids',
    'unassigned_evidence_ids', 'scope_proofs_previously_deferred', 'assertion_ids', 'endpoint_ids',
    'condition_for_assertion_ids', 'exception_for_assertion_ids'}
PROOF_MAPS = {'evidence', 'context_dependencies', 'temporal_context', 'endpoint_set'}


def mapped(value, mapping: dict, field: str = ''):
    if isinstance(value, dict):
        return {(mapping.get(key, key) if field in PROOF_MAPS else key): mapped(item, mapping, key)
                for key, item in value.items()}
    if isinstance(value, list):
        return [mapping.get(item, item) if field in REFERENCE_FIELDS and isinstance(item, str)
                else mapped(item, mapping, field) for item in value]
    return mapping.get(value, value) if field in {'evidence_id', 'id', 'entity_id', 'source_id', 'target_id'} and isinstance(value, str) else value


def value_states(value, *, outbound: bool, field: str = ''):
    """Rename only the assertion state field; never rewrite quotes, scalar text or time roles."""
    if isinstance(value, dict):
        return {key: value_states(item, outbound=outbound, field=key) for key, item in value.items()}
    if isinstance(value, list):
        return [value_states(item, outbound=outbound, field=field) for item in value]
    before, after = ('unknown', 'source_unspecified') if outbound else ('source_unspecified', 'unknown')
    return after if field == 'value_state' and value == before else value


def restore(value: dict, reverse: dict) -> dict:
    return value_states(mapped(value, reverse), outbound=False)


def references(values: list, maximum: int, minimum: int = 0) -> tuple:
    return (list[Literal[tuple(values)]] if values else list[str],
            Field(min_length=minimum, max_length=maximum if values else 0) if minimum else
            Field(default_factory=list, max_length=maximum if values else 0))


def offered_contract(contract, wire: dict):
    """Restrict every reference to existing objects/proofs; new extraction IDs remain local."""
    proofs = list(wire.get('evidence', {}))
    scope = create_model('OfferedScope', __base__=CompilationScope, evidence_ids=references(proofs, 12, 1))
    time = create_model('OfferedTime', __base__=CompilationTime, evidence_ids=references(proofs, 12))
    scoped = {'evidence_ids': references(proofs, 12, 1), 'condition_ids': references(proofs, 12),
              'exception_ids': references(proofs, 12), 'scope': (list[scope], Field(default_factory=list, max_length=12)),
              'temporal': (list[time], Field(default_factory=list, max_length=8))}
    draft = wire.get('draft', {})
    claims = [a['id'] for a in draft.get('assertions', []) if 'id' in a]
    if contract is PacketDraft:
        entity = create_model('OfferedEntity', __base__=CompilationEntity, evidence_ids=references(proofs, 12, 1))
        assertion = create_model('OfferedAssertion', __base__=CompilationAssertion,
            value_state=(Literal['present', 'source_unspecified', 'conflict'], Field(
                description='present requires a nonempty value; source_unspecified/conflict require null. This is a source value state, not a review verdict.')),
            **scoped)
        return create_model('OfferedPacketDraft', __base__=PacketDraft,
            entities=(list[entity], Field(default_factory=list, max_length=32)),
            assertions=(list[assertion], Field(default_factory=list, max_length=48)),
            deferred_evidence_ids=references(proofs, 128))
    if contract is SynthesisDraft:
        endpoints = [*claims, *(e['id'] for e in draft.get('entities', []))]
        endpoint = Literal[tuple(endpoints)] if endpoints else str
        relation = create_model('OfferedRelation', __base__=CompilationRelation,
            source_id=(endpoint, ...), target_id=(endpoint, ...), **scoped)
        section = create_model('OfferedSection', __base__=CompilationSection, assertion_ids=references(claims, 24, 1))
        return create_model('OfferedSynthesisDraft', __base__=SynthesisDraft,
            relations=(list[relation], Field(default_factory=list, max_length=64)),
            sections=(list[section], Field(min_length=1, max_length=32)))
    if contract is PacketCheck:
        from app.modules.knowledge.compilation_runtime_schemas import ItemCheck
        entry = create_model('OfferedItemCheck', __base__=ItemCheck,
            id=(Literal[tuple(claims)] if claims else str, ...), evidence_ids=references(proofs, 24, 1))
        return create_model('OfferedPacketCheck', __base__=PacketCheck,
            items=(list[entry], Field(default_factory=list, max_length=48 if claims else 0)),
            missed_evidence_ids=references(proofs, 128))
    if contract is RelationDirections:
        from app.modules.knowledge.compilation_runtime_schemas import DirectedWitness
        pairs = wire.get('pairs', [])
        ids = [p['id'] for p in pairs]
        endpoints = sorted({pid for pair in pairs for pid in pair['endpoint_set']})
        endpoint = Literal[tuple(endpoints)] if endpoints else str
        entry = create_model('OfferedDirection', __base__=DirectedWitness,
            id=(Literal[tuple(ids)] if ids else str, ...), source_id=(endpoint | None, None),
            target_id=(endpoint | None, None), evidence_ids=references(proofs, 24))
        return create_model('OfferedDirections', __base__=RelationDirections,
            items=(list[entry], Field(max_length=64 if ids else 0)))
    if contract is SynthesisCheck:
        from app.modules.knowledge.compilation_runtime_schemas import ItemCheck, SectionCheck
        synthesis = wire.get('synthesis', {})
        ids = [r['id'] for r in synthesis.get('relations', [])]
        entry = create_model('OfferedRelationCheck', __base__=ItemCheck,
            id=(Literal[tuple(ids)] if ids else str, ...), evidence_ids=references(proofs, 24, 1))
        indices = list(range(len(synthesis.get('sections', []))))
        section = create_model('OfferedSectionCheck', __base__=SectionCheck,
            index=(Literal[tuple(indices)] if indices else int, ...), assertion_ids=references(claims, 24, 1))
        return create_model('OfferedSynthesisCheck', __base__=SynthesisCheck,
            relations=(list[entry], Field(default_factory=list, max_length=64 if ids else 0)),
            sections=(list[section], Field(min_length=1, max_length=64)))
    return contract


def prepare(contract, payload: dict) -> tuple:
    handles = {pid: f'u{index}' for index, pid in enumerate(payload.get('evidence', {}))}
    if contract is not PacketDraft:
        # Review/synthesis may reference existing objects. Extraction creates its own local IDs.
        objects = {**payload.get('draft', {}), 'existing_assertions': payload.get('existing_assertions', []),
                   'direct_assertions': payload.get('assertions', []), 'pairs': payload.get('pairs', []),
                   'relations': payload.get('synthesis', {}).get('relations', [])}
        for category, prefix in [('entities', 'ent'), ('assertions', 'claim'), ('existing_assertions', 'claim'),
                                 ('direct_assertions', 'claim'), ('relations', 'rel'), ('pairs', 'rel')]:
            for item in objects.get(category, []):
                if 'id' in item:
                    handles.setdefault(item['id'], prefix + str(sum(value.startswith(prefix) for value in handles.values())))
    wire = value_states(mapped(payload, handles), outbound=True)
    # Context dependency lists are proof lists keyed by proof ID, not natural language.
    if 'context_dependencies' in payload:
        wire['context_dependencies'] = {handles[pid]: [handles.get(ref, ref) for ref in refs]
                                       for pid, refs in payload['context_dependencies'].items()}
    if contract is TopicSelection and handles:
        offered = Literal[tuple(handles[pid] for pid in payload['evidence'])]
        contract = create_model('OfferedCompilationTopic', __base__=TopicSelection,
            relevant_evidence_ids=(list[offered], Field(default_factory=list, max_length=128)),
            unrelated_evidence_ids=(list[offered], Field(default_factory=list, max_length=128)))
    if contract is CoverageAudit:
        proof = Literal[tuple(handles[pid] for pid in payload['missed_evidence_ids'])]
        claims = [handles[item['id']] for item in payload['existing_assertions']]
        refs = list[Literal[tuple(claims)]] if claims else list[str]
        entry = create_model('OfferedCoverageItem', __base__=CoverageItem,
            evidence_id=(proof, ...), assertion_ids=(refs, Field(default_factory=list, max_length=48 if claims else 0)))
        contract = create_model('OfferedCoverageAudit', __base__=CoverageAudit, items=(list[entry], Field(max_length=128)))
    return offered_contract(contract, wire), wire, {value: key for key, value in handles.items()}


def request_budget(contract, instruction: str, payload: dict, policy, *, feedback_reserve: int = 0) -> dict:
    from app.modules.knowledge.services.wiki_budget import request_usage
    prepared, wire, _ = prepare(contract, payload)
    return request_usage(prepared, instruction + TRANSPORT_NOTE, wire, policy, feedback_reserve=feedback_reserve)
