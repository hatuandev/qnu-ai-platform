"""An impossible coverage role is a completed contract rejection, not a valid audit."""
import json
from unittest.mock import AsyncMock, patch

import pytest

from app.core.exceptions import AppException
from app.modules.knowledge.compilation_runtime_schemas import CoverageAudit
from app.modules.knowledge.services.compilation_modelops import generator
from app.modules.modelops.schemas import LLMGenerateResponse


class Session:
    async def __aenter__(self):
        return None

    async def __aexit__(self, *_):
        return None


@pytest.mark.asyncio
@pytest.mark.parametrize('role,has_assertions,refs,valid',[
    ('supporting_context',False,[],False),
    ('supporting_context',True,[],False),
    ('unrelated',True,['claim0'],False),
    ('supporting_context',True,['claim0'],True),
    ('unrelated',False,[],True),
    ('unresolved',False,[],True),
    ('required_assertion',False,[],True),
])
async def test_real_json_adapter_enforces_coverage_role_cardinality(role,has_assertions,refs,valid):
    payload={'topic':'Quantity','evidence':{'p':{'quote':'Raw evidence','source_revision_id':'s'}},
        'missed_evidence_ids':['p'],'existing_assertions':
            [{'id':'a','entity_id':'e','evidence_ids':['p']}] if has_assertions else []}
    response=LLMGenerateResponse(content=json.dumps({'items':[{'evidence_id':'u0','role':role,
        'assertion_ids':refs,'reason':'A model-supplied role still needs a valid structural binding.'}]}),
        provider='fixture',model='fixture-model',finish_reason='stop',prompt_tokens=100,completion_tokens=20)
    fake=AsyncMock(return_value=response)
    metrics=[]
    with (patch('app.core.database.AsyncSessionFactory',return_value=Session()),
          patch('app.modules.modelops.service.modelops_service.generate',fake)):
        run=generator({'preferred_provider_id':'p','preferred_model_name':'fixture-model'},'default',metrics)
        if valid:
            result=await run(CoverageAudit,'Classify offered proof roles.',payload)
            assert result.items[0].role==role
        else:
            with pytest.raises(AppException) as failure:
                await run(CoverageAudit,'Classify offered proof roles.',payload)
            assert failure.value.code=='KNOWLEDGE_WIKI_INVALID'
            assert failure.value.details['reason']=='json_contract'
        fake.assert_awaited_once()
        assert metrics[-1]['finish_reason']=='stop'
