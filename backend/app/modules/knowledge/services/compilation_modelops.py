"""Resolve existing ModelOps defaults once; reuse its structured, budgeted adapter."""
import hashlib
import json
from itertools import pairwise

from sqlalchemy import select

from app.core.exceptions import AppException
from app.modules.knowledge.compilation_runtime_schemas import CompilerPolicy
from app.modules.knowledge.services.compilation_coverage import SOURCE_LIMITATIONS
from app.modules.knowledge.services.compilation_transport import (
    TRANSPORT_NOTE,
    VALUE_STATE_CONTRACT,
    prepare,
    restore,
    wire_instruction,
)
from app.modules.knowledge.services.wiki_build import generate_object
from app.modules.knowledge.services.wiki_compiler import digest
from app.modules.knowledge.wiki_schemas import WikiPolicy


async def resolve_route(db, *, model_override: str | None = None) -> dict:
    from app.modules.modelops.services.model_catalog_service import model_catalog_service

    defaults = (await model_catalog_service.get_system_model_defaults(db)).defaults
    if not defaults.default_chat_provider_id or not defaults.default_chat_model:
        raise AppException('Chưa cấu hình model biên soạn trong ModelOps.',
            code='KNOWLEDGE_COMPILATION_MODEL_REQUIRED', status_code=409)
    route = {'preferred_provider_id': defaults.default_chat_provider_id,
             'preferred_model_name': model_override or defaults.default_chat_model}
    if defaults.default_chat_mode == 'combo':
        chain = [item for item in defaults.chat_combo_chain if item.is_active]
        for current, following in pairwise(chain):
            if (current.provider_id, current.model_name) == (route['preferred_provider_id'], route['preferred_model_name']):
                route.update(fallback_provider_id=following.provider_id, fallback_model_name=following.model_name)
                break
    from app.modules.modelops.models import ModelProviderConfig

    ids = [route['preferred_provider_id'], route.get('fallback_provider_id'), 'system_model_defaults']
    rows = (await db.scalars(select(ModelProviderConfig).where(ModelProviderConfig.id.in_(ids)))).all()
    route['_request_timeout_seconds'] = max(((getattr(row, 'timeout_seconds', None) or 30) for row in rows
        if row.id in {route['preferred_provider_id'], route.get('fallback_provider_id')}), default=30)
    # Hash configuration in memory, including protected credential rotation; never return its plaintext/ciphertext.
    route['_configuration_hash'] = hashlib.sha256(json.dumps(
        {row.id: {c.key: getattr(row, c.key) for c in row.__table__.columns} for row in rows},
        sort_keys=True, default=str).encode()).hexdigest()
    from app.modules.modelops.services.token_limits import configured_token_limits

    route['_token_limits'] = []
    by_id = {row.id: row for row in rows}
    for prefix in ('preferred', 'fallback'):
        provider, model = route.get(prefix + '_provider_id'), route.get(prefix + '_model_name')
        row = by_id.get(provider)
        if row and model:
            limits = configured_token_limits(getattr(row, 'extra_config', None), model, getattr(row, 'api_base_url', None))
            if limits is None and prefix=='preferred':
                from app.modules.modelops.services.capacity_discovery import discover

                limits=await discover(row,model,db)
            route['_token_limits'].append({'provider_id': provider, 'model': model,
                **(limits or {'basis': 'discover_on_dispatch_unverified'})})
    return route


def execution_policy(route: dict) -> CompilerPolicy:
    # Only server-resolved route metadata may configure compiler execution.
    configured = route.get('_compiler_policy') or {}
    profiles = route.get('_token_limits') or []
    primary=next((p for p in profiles if p.get('provider_id')==route.get('preferred_provider_id')
                  and p.get('model')==route.get('preferred_model_name')),profiles[0] if profiles else None)
    if '_token_limits' in route and (not primary or not primary.get('context_window_tokens')):
        raise AppException('Model chưa khai báo capacity cho endpoint hiện tại; chưa gọi compiler.',
            code='MODEL_TOKEN_CAPACITY_REQUIRED',status_code=422)
    if primary and primary.get('reasoning_in_output_budget') is False:
        raise AppException('Provider chưa có ngân sách thinking tách riêng được xác nhận.',
            code='MODEL_REASONING_BUDGET_UNVERIFIED', status_code=422)
    selected = {'request_timeout_seconds': route.get('_request_timeout_seconds', 30), **configured}
    if primary:
        # Each dispatch checks its own endpoint. A smaller fallback must not
        # silently reduce the primary's capacity or crop its source evidence.
        selected['context_budget_tokens'] = primary['context_window_tokens']
        selected['max_output_tokens'] = primary.get('max_output_tokens') or primary['context_window_tokens']
        selected.update(automatic_output_budget=True,tokenizer_encoding=primary.get('tokenizer_encoding'),
                        chat_overhead_tokens=primary.get('chat_overhead_tokens',0))
        for name in ('context_budget_tokens', 'max_output_tokens'):
            if name in configured:
                selected[name] = min(selected[name], configured[name])
        selected['token_budget_basis']='configured_primary_model_capacity'
    if not selected.get('automatic_output_budget') and selected.get('max_output_tokens',2500)>=selected.get('context_budget_tokens',24000):
        raise AppException('Ngân sách sinh không chừa chỗ cho dữ liệu đầu vào.',
            code='MODEL_TOKEN_LIMITS_INVALID', status_code=422)
    return CompilerPolicy.model_validate(selected)


def transport_policy(policy: CompilerPolicy) -> WikiPolicy:
    return WikiPolicy(**{k:getattr(policy,k) for k in ('max_output_tokens','context_budget_tokens',
        'automatic_output_budget','tokenizer_encoding','chat_overhead_tokens')})


def generator(route: dict, tenant_id: str, metrics: list):
    from app.core.database import AsyncSessionFactory

    async def generate(contract, instruction, payload):
        async with AsyncSessionFactory() as inference_db:
            wire_contract, wire, reverse = prepare(contract, payload)
            instruction = wire_instruction(contract, instruction, payload) + TRANSPORT_NOTE
            policy = execution_policy(route)
            options = {'reasoning_effort': policy.reasoning_effort} if policy.reasoning_effort is not None else {}
            result = await generate_object(inference_db, tenant_id, {k: v for k, v in route.items() if not k.startswith('_')},
                                           transport_policy(policy), metrics, wire_contract, instruction, wire, **options)
            if metrics[-1].get('finish_reason') not in {None, 'stop'}:
                raise AppException('Mô hình chưa hoàn thành đầu ra biên soạn.',
                    code='KNOWLEDGE_COMPILATION_INCOMPLETE_OUTPUT', status_code=502)
            value = restore(result.model_dump(), reverse)
            from app.modules.knowledge.services.compilation_columns import (
                ColumnRole,
                materialize_column_review,
            )

            if contract is ColumnRole:
                value=materialize_column_review(value,payload)
            if payload.get('source_grounded_review_protocol'):
                from app.modules.knowledge.services.compilation_grounding import (
                    materialize_packet_review,
                )

                value=materialize_packet_review(value,payload)
            if payload.get('source_grounding_protocol'):
                from app.modules.knowledge.compilation_runtime_schemas import (
                    PacketDraft,
                    SynthesisCheck,
                    SynthesisDraft,
                )
                from app.modules.knowledge.services.compilation_grounding import (
                    materialize_packet,
                    materialize_section_reviews,
                    materialize_synthesis,
                )

                if contract is PacketDraft:
                    value = materialize_packet(value, payload)
                elif contract is SynthesisDraft:
                    value = materialize_synthesis(value, payload)
                elif contract is SynthesisCheck:
                    value = materialize_section_reviews(value,payload)
            return contract.model_validate(value)
    return generate


def configuration_hash(route: dict, policy: dict) -> str:
    from app.modules.knowledge.compilation_runtime_schemas import (
        REVIEW_REASON_MAX_CHARS,
        PacketCoverage,
    )
    from app.modules.knowledge.services import compilation_engine as instructions
    from app.modules.knowledge.services.compilation_candidate_repair import (
        PROTOCOL as REPAIR_PROTOCOL,
    )
    from app.modules.knowledge.services.compilation_columns import (
        FIELD_INSTRUCTION,
        FIELD_PROTOCOL,
        ColumnRole,
        TableFields,
    )
    from app.modules.knowledge.services.compilation_columns import INSTRUCTION as COLUMN_INSTRUCTION
    from app.modules.knowledge.services.compilation_columns import PROTOCOL as COLUMN_PROTOCOL
    from app.modules.knowledge.services.compilation_coverage import CAPACITY_POLICY, COVERAGE
    from app.modules.knowledge.services.compilation_cross_source import PROPOSE, PROTOCOL, VERIFY
    from app.modules.knowledge.services.compilation_grounding import (
        EXTRACT,
        RECORD_EXTRACT,
        REVIEW,
        SYNTHESIS_REVIEW,
        SYNTHESIZE,
        GroundedPacket,
        GroundedSynthesis,
    )
    from app.modules.knowledge.services.compilation_grounding import PROTOCOL as GROUNDING_PROTOCOL
    from app.modules.knowledge.services.compilation_grounding import (
        REVIEW_PROTOCOL as GROUNDED_REVIEW_PROTOCOL,
    )
    from app.modules.knowledge.services.compilation_metrics import PROTOCOL as METRIC_PROTOCOL
    from app.modules.knowledge.services.compilation_repair_selection import (
        INSTRUCTION as REPAIR_SELECTION,
    )
    from app.modules.knowledge.services.compilation_repair_selection import RepairSelectionCheck
    from app.modules.knowledge.services.compilation_review import (
        COVERAGE_ONLY,
        GROUNDING_AUDIT_PROTOCOL,
        REVIEW_PROTOCOL,
        TEMPORAL_REVIEW,
    )
    from app.modules.knowledge.services.compilation_span_menu import PROTOCOL as SPAN_MENU_PROTOCOL
    from app.modules.knowledge.services.compilation_structure import PROTOCOL as STRUCTURE_PROTOCOL
    from app.modules.modelops.services.capacity_discovery import PROTOCOL as CAPACITY_PROTOCOL
    prompts={name:getattr(instructions,name) for name in (
        'DRAFT','REVIEW','SYNTHESIZE','VERIFY_SYNTHESIS','SELECT_TOPIC','VERIFY_TOPIC','VERIFY_PRIMARY','DIRECTION_REVIEW')}
    prompts['COVERAGE']=COVERAGE
    return digest({'route': route, 'policy': policy, 'transport': transport_policy(CompilerPolicy.model_validate(policy)).model_dump(),
                   'checkpoint_protocol': 'completed-candidates-ordinal-and-exact-request/v1',
                   'aggregate_protocol': 'bounded-groups-manifest/v2',
                   'cross_group_protocol': {'version': PROTOCOL, 'instruction_hash': digest([PROPOSE, VERIFY])},
                   'packing_protocol': 'source-rendered-synthesis-review-envelope/v2',
                   'token_capacity_protocol': CAPACITY_PROTOCOL,
                   'source_span_menu_protocol': SPAN_MENU_PROTOCOL,
                   'structure_protocol': STRUCTURE_PROTOCOL,
                   'metric_protocol': METRIC_PROTOCOL,
                   'source_grounding': {'version': GROUNDING_PROTOCOL, 'instruction_hash':digest([EXTRACT,RECORD_EXTRACT,SYNTHESIZE])},
                   'grounded_review':{'version':GROUNDED_REVIEW_PROTOCOL,'instruction_hash':digest([REVIEW,SYNTHESIS_REVIEW])},
                   'grounded_audit_separation':{'version':GROUNDING_AUDIT_PROTOCOL,'coverage':digest([COVERAGE_ONLY,PacketCoverage.model_json_schema()])},
                   'semantic_repair':{'protocol':REPAIR_PROTOCOL,
                       'selection':digest([REPAIR_SELECTION,RepairSelectionCheck.model_json_schema()])},
                   'source_grounding_schemas':digest([GroundedPacket.model_json_schema(),GroundedSynthesis.model_json_schema()]),
                   'grounded_role_policy':'primary-scalar-nonnumeric-subject-verified-header-context/v1',
                   'span_menu_policy':'lexical-quantity-role-and-assertion-heading/v3-raw-evidence-intact',
                   'section_review_scope':'fixed-complete-request-membership/v1',
                   'column_roles': {'version':COLUMN_PROTOCOL,'instruction_hash':digest(COLUMN_INSTRUCTION),'schema':digest(ColumnRole.model_json_schema())},
                   'table_fields':{'version':FIELD_PROTOCOL,'instruction_hash':digest(FIELD_INSTRUCTION),'schema':digest(TableFields.model_json_schema())},
                   'coverage_capacity_policy': CAPACITY_POLICY,
                   'review_reason_limit': REVIEW_REASON_MAX_CHARS,
                   'instruction_hash':digest(prompts),
                   'review_protocol':REVIEW_PROTOCOL, 'temporal_review_hash':digest(TEMPORAL_REVIEW),
                   'value_state_contract':VALUE_STATE_CONTRACT, 'transport_instruction_hash':digest(TRANSPORT_NOTE),
                   'proof_handles': 'compilation-transport/v4-fixed-review-scope-counter-evidence-enums', 'proof_closure': 'explicit-scope/v1',
                   'topic_exclusion': 'both-explicit-only/v1', 'format_correction': 'one-known-rejection-measured-envelope/v2',
                   'topic_refinement':instructions.TOPIC_REFINEMENT,
                   'topic_cache': 'per-source/v1', 'inventory_accounting': 'primary-and-offered-context/v2',
            'semantic_boundaries': 'literal-scope-source-year-section/blind-endpoint-set/v3',
                   'qualifier_review': 'explicit-bound-raw-views/v1',
                   'temporal_role_guide': 'source-reported-five-roles/v1', 'synthesis_grouping': 'whole-source-if-fits/v1',
                   'source_limitations': {'version': 'negative-and-partial-evidence/v1',
                                          'sha256': digest(SOURCE_LIMITATIONS)},
                   'packet_entity_graph': 'validated-local-objects/v1', 'scalar_errors': 'actionable-state-codes/v1'})
