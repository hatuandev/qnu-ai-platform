"""Request-local proof handles; durable revision/hash catalog never comes from the model."""
from typing import Literal

from pydantic import Field, create_model

from app.modules.knowledge.compilation_runtime_schemas import (
    CoverageAudit,
    CoverageItem,
    CrossRelationCheck,
    CrossRelationDraft,
    PacketCheck,
    PacketCoverage,
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

REFERENCE_FIELDS = {'evidence_ids', 'counter_evidence_ids', 'condition_ids', 'exception_ids', 'deferred_evidence_ids',
    'relevant_evidence_ids', 'unrelated_evidence_ids', 'primary_evidence_ids', 'missed_evidence_ids',
    'unassigned_evidence_ids', 'scope_proofs_previously_deferred', 'assertion_ids', 'endpoint_ids',
    'condition_for_assertion_ids', 'exception_for_assertion_ids', 'section_evidence_ids',
    'header_evidence_ids', 'table_preamble_evidence_ids', 'explicit_context_evidence_ids', 'body_evidence_ids', 'context_evidence_ids'}
PROOF_MAPS = {'evidence', 'context_dependencies', 'temporal_context', 'endpoint_set'}


def mapped(value, mapping: dict, field: str = ''):
    if isinstance(value, dict):
        return {(mapping.get(key, key) if field in PROOF_MAPS else key): mapped(item, mapping, key)
                for key, item in value.items()}
    if isinstance(value, list):
        return [mapping.get(item, item) if field in REFERENCE_FIELDS and isinstance(item, str)
                else mapped(item, mapping, field) for item in value]
    return mapping.get(value, value) if field in {'evidence_id', 'candidate_evidence_id', 'context_evidence_id', 'id', 'entity_id', 'source_id', 'target_id'} and isinstance(value, str) else value


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
    from app.modules.knowledge.services.compilation_repair_selection import (
        RepairReplacement,
        RepairSelectionCheck,
    )

    if contract is RepairSelectionCheck:
        ids = [a['id'] for a in wire['repair_targets']]
        claims = [a['id'] for a in wire['draft']['assertions']]
        entry = create_model('OfferedRepairReplacement', __base__=RepairReplacement,
            id=(Literal[tuple(ids)], ...), assertion_ids=references(claims, 48))
        return create_model('OfferedRepairSelectionCheck', __base__=RepairSelectionCheck,
            items=(list[entry], Field(max_length=48)), missed_evidence_ids=references(proofs, 128))
    scope = create_model('OfferedScope', __base__=CompilationScope, evidence_ids=references(proofs, 12, 1))
    time = create_model('OfferedTime', __base__=CompilationTime, evidence_ids=references(proofs, 12))
    scoped = {'evidence_ids': references(proofs, 12, 1), 'condition_ids': references(proofs, 12),
              'exception_ids': references(proofs, 12), 'scope': (list[scope], Field(default_factory=list, max_length=12)),
              'temporal': (list[time], Field(default_factory=list, max_length=8))}
    draft = wire.get('draft', {})
    claims = [a['id'] for a in draft.get('assertions', []) if 'id' in a]
    from app.modules.knowledge.services.compilation_columns import ColumnRole, TableFields
    from app.modules.knowledge.services.compilation_grounding import (
        GroundedClaim,
        GroundedPacket,
        GroundedScope,
        GroundedSection,
        GroundedSynthesis,
        SourceSpan,
        extraction_choices,
    )

    if contract is ColumnRole:
        from app.modules.knowledge.compilation_schemas import CompilationContract

        return create_model('OfferedFixedColumnAudit',__base__=CompilationContract,
            role=ColumnRole.model_fields['role'].rebuild_annotation(),
            counter_evidence_ids=references(proofs,9),reason=(str,Field(min_length=1,max_length=1000)))
    if contract is PacketCoverage:
        return create_model('OfferedPacketCoverage',__base__=PacketCoverage,
            missed_evidence_ids=(references(proofs,128)[0],Field(max_length=128 if proofs else 0)))
    if contract is TableFields:
        metric_ids=wire.get('context_evidence_ids',[])
        return create_model('OfferedTableFields',__base__=TableFields,
            context_evidence_id=(Literal[tuple(metric_ids)] if metric_ids else str,...),temporal=scoped['temporal'])
    if wire.get('source_grounding_protocol') and contract in {PacketDraft, SynthesisDraft}:
        labels = [q for q, value in wire.get('source_spans', {}).items() if len(value['literal'])<=200]
        label_span = create_model('OfferedLabelSpan', __base__=SourceSpan,
                                 span_id=(Literal[tuple(labels)] if labels else str, ...))
        if contract is PacketDraft:
            records=list(wire.get('table_records',{}))
            if wire.get('records_only'):
                return create_model('OfferedRecordSelection',__base__=GroundedPacket,
                    record_ids=references(records,32),claims=(list[str],Field(default_factory=list,max_length=0)),
                    deferred_evidence_ids=references(proofs,128))
            subjects,metrics,scalars = extraction_choices(payload=wire, choices=wire.get('source_spans',{}))
            def select_span(name, values):
                return create_model(name,__base__=SourceSpan,span_id=(Literal[tuple(values)] if values else str,...))
            subject_span=select_span('OfferedSubjectSpan',subjects)
            metric_span=select_span('OfferedMetricSpan',metrics)
            scalar_span=select_span('OfferedPrimaryScalarSpan',scalars)
            scope_span = create_model('OfferedGroundedScope', __base__=GroundedScope, anchor=(label_span, ...))
            from app.modules.knowledge.services.compilation_grounding import prose_primary

            claim = create_model('OfferedGroundedClaim', __base__=GroundedClaim,
                subject=(subject_span, ...), metric=(metric_span, ...),
                column=(type(None) if prose_primary(wire) else label_span | None, None), scalar=(scalar_span | None, None),
                limitation=(scalar_span | None, None), unit=(label_span | None, None),
                value_state=(Literal['present', 'source_unspecified', 'conflict'], ...),
                scope=(list[scope_span], Field(default_factory=list, max_length=8)),
                temporal=scoped['temporal'], condition_ids=scoped['condition_ids'], exception_ids=scoped['exception_ids'])
            return create_model('OfferedGroundedPacket', __base__=GroundedPacket,
                record_ids=references(records,32),
                claims=(list[claim], Field(default_factory=list, max_length=32 if subjects and metrics and scalars else 0)),
                deferred_evidence_ids=references(proofs, 128))
        section = create_model('OfferedGroundedSection', __base__=GroundedSection,
            heading=(label_span, ...), assertion_ids=references(claims, 24, 1))
        # Reuse the existing endpoint/scoped relation contract, never free model IDs.
        relation_contract = offered_contract(SynthesisDraft, {k:v for k,v in wire.items() if k!='source_grounding_protocol'})
        return create_model('OfferedGroundedSynthesis', __base__=GroundedSynthesis,
            sections=(list[section], Field(min_length=1, max_length=32)),
            relations=relation_contract.model_fields['relations'].rebuild_annotation())
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
    if contract in {SynthesisDraft, CrossRelationDraft}:
        endpoints = [*claims, *(e['id'] for e in draft.get('entities', []))]
        endpoint = Literal[tuple(endpoints)] if endpoints else str
        relation = create_model('OfferedRelation', __base__=CompilationRelation,
            source_id=(endpoint, ...), target_id=(endpoint, ...), **scoped)
        if contract is CrossRelationDraft:
            return create_model('OfferedCrossRelations', __base__=CrossRelationDraft,
                relations=(list[relation], Field(default_factory=list, max_length=64)))
        section = create_model('OfferedSection', __base__=CompilationSection, assertion_ids=references(claims, 24, 1))
        return create_model('OfferedSynthesisDraft', __base__=SynthesisDraft,
            relations=(list[relation], Field(default_factory=list, max_length=64)),
            sections=(list[section], Field(min_length=1, max_length=32)))
    if contract is CrossRelationCheck:
        from app.modules.knowledge.compilation_runtime_schemas import ItemCheck
        ids = [r['id'] for r in wire.get('synthesis', {}).get('relations', [])]
        entry = create_model('OfferedCrossRelationCheck', __base__=ItemCheck,
            id=(Literal[tuple(ids)] if ids else str, ...), evidence_ids=references(proofs, 24, 1))
        return create_model('OfferedCrossRelationChecks', __base__=CrossRelationCheck,
            items=(list[entry], Field(default_factory=list, max_length=64 if ids else 0)))
    if contract is PacketCheck:
        from app.modules.knowledge.compilation_runtime_schemas import ItemCheck
        if wire.get('source_grounded_review_protocol'):
            from app.modules.knowledge.compilation_schemas import CompilationContract

            validity=Literal['valid','invalid','not_checked']
            entry=create_model('OfferedExplicitValidityCheck',__base__=CompilationContract,
                id=(Literal[tuple(claims)] if claims else str,...),
                verdict=ItemCheck.model_fields['verdict'].rebuild_annotation(),
                entity_validity=(validity,...),temporal_validity=(validity,...),qualifier_validity=(validity,...),
                counter_evidence_ids=references(proofs,12),reason=(str,Field(min_length=1,max_length=4096)))
        else:
            entry = create_model('OfferedItemCheck', __base__=ItemCheck,
                id=(Literal[tuple(claims)] if claims else str, ...), evidence_ids=references(proofs, 24, 1))
        return create_model('OfferedPacketCheck', __base__=PacketCheck,
            items=(list[entry], Field(default_factory=list, max_length=48 if claims else 0)),
            missed_evidence_ids=references([] if wire.get('source_grounded_review_protocol') else proofs, 128))
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
        if wire.get('source_grounding_protocol'):
            from app.modules.knowledge.compilation_schemas import CompilationContract

            section=create_model('OfferedCompleteSectionVerdict',__base__=CompilationContract,
                index=(Literal[tuple(indices)] if indices else int,...),
                verdict=SectionCheck.model_fields['verdict'].rebuild_annotation(),
                reason=(str,Field(min_length=1,max_length=4096)))
        else:
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
                                 ('direct_assertions', 'claim'), ('relations', 'rel'), ('pairs', 'rel'),
                                 ('repair_targets', 'claim'), ('repair_target_entities', 'ent')]:
            for item in objects.get(category, payload.get(category, [])):
                if 'id' in item:
                    handles.setdefault(item['id'], prefix + str(sum(value.startswith(prefix) for value in handles.values())))
    wire = value_states(mapped(payload, handles), outbound=True)
    if payload.get('source_grounding_protocol') and contract in {PacketDraft,SynthesisDraft}:
        from app.modules.knowledge.services.compilation_span_menu import (
            PROTOCOL as SPAN_MENU_PROTOCOL,
        )
        from app.modules.knowledge.services.compilation_span_menu import (
            source_span_menu,
        )

        if not payload.get('records_only') or contract is SynthesisDraft:
            wire['source_span_protocol']=SPAN_MENU_PROTOCOL
            wire['source_span_offset_basis']='evidence.quote/unicode-codepoints/end-exclusive'
            wire['source_spans']=source_span_menu(payload,handles,headings=contract is SynthesisDraft)
    temporal = wire.get('temporal_context')
    if temporal and all(isinstance(value, dict) and set(value)=={'origin','authority','scope_hint'}
                        for value in temporal.values()):
        policies = {(value['origin'],value['authority']) for value in temporal.values()}
        if len(policies)==1:
            origin,authority = next(iter(policies))
            wire['temporal_navigation_policy'] = {'origin':origin,'authority':authority}
            wire['temporal_context'] = {pid:value['scope_hint'] for pid,value in temporal.items()}
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


def request_budget(contract, instruction: str, payload: dict, policy, *, feedback_reserve: int = 0,
                   reserve_minimal_correction: bool = False) -> dict:
    from app.modules.knowledge.services.wiki_budget import request_usage
    prepared, wire, _ = prepare(contract, payload)
    instruction = wire_instruction(contract, instruction, payload)
    initial = request_usage(prepared, instruction + TRANSPORT_NOTE, wire, policy, feedback_reserve=feedback_reserve)
    if not reserve_minimal_correction or 'output_format_feedback' in payload:
        return initial  # The one permitted correction never reserves another retry.
    # Both known parser errors fit this measured envelope. Its field changes no
    # proof/object handles or output schema; never reserve an arbitrary token block.
    correction = request_usage(prepared, instruction + TRANSPORT_NOTE,
        {**wire,'output_format_feedback':{'reason':'json_contract'}}, policy, feedback_reserve=feedback_reserve)
    return {**correction,'initial_request_total_reserved':initial['total_reserved'],
            'minimal_format_correction_reserved':True}


def planned_request_budget(contract, instruction: str, payload: dict, policy, *, feedback_reserve: int = 0) -> dict:
    return request_budget(contract,instruction,payload,policy,feedback_reserve=feedback_reserve,
                          reserve_minimal_correction=True)


def wire_instruction(contract, instruction: str, payload: dict) -> str:
    if contract is PacketCheck and payload.get('source_grounded_review_protocol'):
        from app.modules.knowledge.services.compilation_grounding import REVIEW

        return REVIEW
    if payload.get('source_grounding_protocol'):
        from app.modules.knowledge.services.compilation_grounding import (
            EXTRACT,
            RECORD_EXTRACT,
            SYNTHESIZE,
        )

        if contract is PacketDraft:
            return RECORD_EXTRACT if payload.get('records_only') else EXTRACT
        if contract is SynthesisDraft:
            return SYNTHESIZE
        if contract is SynthesisCheck:
            from app.modules.knowledge.services.compilation_grounding import SYNTHESIS_REVIEW

            return SYNTHESIS_REVIEW
    return instruction
