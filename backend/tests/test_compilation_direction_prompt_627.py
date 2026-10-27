"""The effective grounded request must retain direction semantics and opaque endpoint IDs."""
import json
from copy import deepcopy
from unittest.mock import AsyncMock, patch

import pytest

from app.modules.knowledge.compilation_runtime_schemas import SynthesisDraft
from app.modules.knowledge.services.compilation_engine import SYNTHESIZE
from app.modules.knowledge.services.compilation_grounding import PROTOCOL
from app.modules.knowledge.services.compilation_modelops import generator
from app.modules.knowledge.services.compilation_semantics import DIRECTION_RULES
from app.modules.modelops.schemas import LLMGenerateResponse


class Session:
    async def __aenter__(self):
        return None

    async def __aexit__(self, *_):
        return None


@pytest.mark.asyncio
@pytest.mark.parametrize('kind', list(DIRECTION_RULES))
@pytest.mark.parametrize('newer_first', [False, True])
async def test_grounded_generator_retains_direction_rules_and_selected_endpoints(kind, newer_first):
    evidence={'heading':{'source_revision_id':'source','quote':'Chính sách'},
        'clause':{'source_revision_id':'source','quote':'Sigma: mức mới 109 thay thế mức cũ 73.'}}
    base={'entity_id':'subject','attribute':'Mức','value_state':'present','unit':None,'evidence_ids':['clause'],
          'scope':[],'temporal':[],'condition_ids':[],'exception_ids':[]}
    assertions=[{**deepcopy(base),'id':'opaque-first','value':'73'},
                {**deepcopy(base),'id':'opaque-second','value':'109'}]
    if newer_first:
        assertions.reverse()
    payload={'source_grounding_protocol':PROTOCOL,'evidence':evidence,
        'draft':{'entities':[{'id':'subject','label':'Sigma','evidence_ids':['clause']}],
                 'assertions':assertions}}

    async def respond(_, request):
        instruction=request.messages[0].content
        assert DIRECTION_RULES[kind] in instruction
        assert 'source_id' in instruction and 'target_id' in instruction
        wire=json.loads(request.messages[-1].content)
        ids={a['value']:a['id'] for a in wire['draft']['assertions']}
        heading=next(q for q,s in wire['source_spans'].items() if s['literal']=='Sigma')
        proof=next(p for p,e in wire['evidence'].items() if e['quote']==evidence['clause']['quote'])
        value={'sections':[{'heading':{'span_id':heading},'assertion_ids':list(ids.values())}],
            'relations':[{'id':'relation','kind':kind,'source_id':ids['109'],'target_id':ids['73'],
                'evidence_ids':[proof]}]}
        return LLMGenerateResponse(content=json.dumps(value,ensure_ascii=False),provider='fixture',
            model='fixture',finish_reason='stop',prompt_tokens=100,completion_tokens=50)

    fake=AsyncMock(side_effect=respond)
    with (patch('app.core.database.AsyncSessionFactory',return_value=Session()),
          patch('app.modules.modelops.service.modelops_service.generate',fake)):
        result=await generator({'preferred_provider_id':'fixture','preferred_model_name':'fixture'},'default',[])(
            SynthesisDraft,SYNTHESIZE,payload)
    fake.assert_awaited_once()
    assert result.relations[0].source_id=='opaque-second'
    assert result.relations[0].target_id=='opaque-first'
    assert result.relations[0].kind==kind
