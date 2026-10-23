"""Resolve existing ModelOps defaults once; reuse its structured, budgeted adapter."""
import hashlib
import json
from itertools import pairwise

from sqlalchemy import select

from app.core.exceptions import AppException
from app.modules.knowledge.services.compilation_coverage import SOURCE_LIMITATIONS
from app.modules.knowledge.services.compilation_transport import (
    TRANSPORT_NOTE,
    VALUE_STATE_CONTRACT,
    prepare,
    restore,
)
from app.modules.knowledge.services.wiki_build import generate_object
from app.modules.knowledge.services.wiki_compiler import digest
from app.modules.knowledge.wiki_schemas import WikiPolicy


async def resolve_route(db) -> dict:
    from app.modules.modelops.services.model_catalog_service import model_catalog_service

    defaults = (await model_catalog_service.get_system_model_defaults(db)).defaults
    if not defaults.default_chat_provider_id or not defaults.default_chat_model:
        raise AppException('Chưa cấu hình model biên soạn trong ModelOps.',
            code='KNOWLEDGE_COMPILATION_MODEL_REQUIRED', status_code=409)
    route = {'preferred_provider_id': defaults.default_chat_provider_id,
             'preferred_model_name': defaults.default_chat_model}
    if defaults.default_chat_mode == 'combo':
        chain = [item for item in defaults.chat_combo_chain if item.is_active]
        for current, following in pairwise(chain):
            if (current.provider_id, current.model_name) == (defaults.default_chat_provider_id, defaults.default_chat_model):
                route.update(fallback_provider_id=following.provider_id, fallback_model_name=following.model_name)
                break
    from app.modules.modelops.models import ModelProviderConfig

    ids = [route['preferred_provider_id'], route.get('fallback_provider_id'), 'system_model_defaults']
    rows = (await db.scalars(select(ModelProviderConfig).where(ModelProviderConfig.id.in_(ids)))).all()
    # Hash configuration in memory, including protected credential rotation; never return its plaintext/ciphertext.
    route['_configuration_hash'] = hashlib.sha256(json.dumps(
        {row.id: {c.key: getattr(row, c.key) for c in row.__table__.columns} for row in rows},
        sort_keys=True, default=str).encode()).hexdigest()
    return route


def generator(route: dict, tenant_id: str, metrics: list):
    from app.core.database import AsyncSessionFactory

    async def generate(contract, instruction, payload):
        async with AsyncSessionFactory() as inference_db:
            wire_contract, wire, reverse = prepare(contract, payload)
            instruction += TRANSPORT_NOTE
            result = await generate_object(inference_db, tenant_id, {k: v for k, v in route.items() if not k.startswith('_')},
                                           WikiPolicy(), metrics, wire_contract, instruction, wire)
            if metrics[-1].get('finish_reason') not in {None, 'stop'}:
                raise AppException('Mô hình chưa hoàn thành đầu ra biên soạn.',
                    code='KNOWLEDGE_COMPILATION_INCOMPLETE_OUTPUT', status_code=502)
            return contract.model_validate(restore(result.model_dump(), reverse))
    return generate


def configuration_hash(route: dict, policy: dict) -> str:
    from app.modules.knowledge.services import compilation_engine as instructions
    from app.modules.knowledge.services.compilation_coverage import COVERAGE
    prompts={name:getattr(instructions,name) for name in (
        'DRAFT','REVIEW','SYNTHESIZE','VERIFY_SYNTHESIS','SELECT_TOPIC','VERIFY_TOPIC','DIRECTION_REVIEW')}
    prompts['COVERAGE']=COVERAGE
    return digest({'route': route, 'policy': policy, 'transport': WikiPolicy().model_dump(),
                   'instruction_hash':digest(prompts),
                   'value_state_contract':VALUE_STATE_CONTRACT, 'transport_instruction_hash':digest(TRANSPORT_NOTE),
                   'proof_handles': 'compilation-transport/v3-all-known-reference-enums', 'proof_closure': 'explicit-scope/v1',
                   'topic_exclusion': 'both-explicit-only/v1', 'format_correction': 'one-known-rejection/v1',
                   'topic_cache': 'per-source/v1', 'inventory_accounting': 'primary-and-offered-context/v2',
            'semantic_boundaries': 'literal-scope-source-year-section/blind-endpoint-set/v3',
                   'qualifier_review': 'explicit-bound-raw-views/v1',
                   'temporal_role_guide': 'source-reported-five-roles/v1', 'synthesis_grouping': 'whole-source-if-fits/v1',
                   'source_limitations': {'version': 'negative-and-partial-evidence/v1',
                                          'sha256': digest(SOURCE_LIMITATIONS)},
                   'packet_entity_graph': 'validated-local-objects/v1', 'scalar_errors': 'actionable-state-codes/v1'})
