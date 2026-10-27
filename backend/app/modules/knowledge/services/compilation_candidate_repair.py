"""One new source-bound candidate after a failed truth audit, never a verdict override."""
from copy import deepcopy

from app.modules.knowledge.compilation_runtime_schemas import PacketDraft
from app.modules.knowledge.services.compilation_review import grounded
from app.modules.knowledge.services.compilation_transport import planned_request_budget
from app.modules.knowledge.services.compilation_validation import supported

LEGACY_PROTOCOL='one-changed-source-bound-semantic-repair-independent-review/v2'
PROTOCOL='source-bound-repair-with-audited-replacement-and-coverage/v3'


def assertion_signature(draft: dict, item: dict) -> str:
    from app.modules.knowledge.services.wiki_compiler import digest

    entity=next(e for e in draft['entities'] if e['id']==item['entity_id'])
    value={k:v for k,v in item.items() if k not in {'id','entity_id'}}
    for key in ('evidence_ids','condition_ids','exception_ids'):
        value[key]=sorted(set(value[key]))
    value['scope']=sorted((s['dimension'],s['value'],sorted(set(s['evidence_ids']))) for s in item['scope'])
    value['temporal']=sorted((t['role'],sorted(set(t['years'])),sorted(set(t['evidence_ids']))) for t in item['temporal'])
    return digest({'entity':{**{k:v for k,v in entity.items() if k not in {'id','evidence_ids'}},
                             'evidence_ids':sorted(set(entity['evidence_ids']))},'assertion':value})


def repeats_failed_assertion(initial: dict, candidate: dict) -> bool:
    failed={item['id'] for item in initial['review']['items'] if not supported(item)}
    previous={assertion_signature(initial['draft'],a) for a in initial['draft']['assertions'] if not failed or a['id'] in failed}
    current={assertion_signature(candidate['draft'],a) for a in candidate['draft']['assertions']}
    return bool(previous & current)


async def repair_semantics(payload: dict, initial: dict, extract, key: str, transport, *, bounded=None, column_roles=None) -> dict:
    failed=[item for item in initial['review']['items'] if not supported(item)]
    issues=initial['review'].get('mechanical_issues',[])
    if not grounded(initial['draft']) or not (failed or issues):
        return initial
    from app.modules.knowledge.services.compilation_engine import DRAFT

    corrected={**payload,'candidate_correction':{'rejected_items':failed,'mechanical_issues':issues,
        'rejected_assertions':[a for a in initial['draft']['assertions'] if a['id'] in {c['id'] for c in failed}],
        'preserve_supported_assertions':[a for a in initial['draft']['assertions'] if a['id'] not in {c['id'] for c in failed}],
        'authority':'critique_only_not_source_or_approval'}}
    budget=planned_request_budget(PacketDraft,DRAFT,corrected,transport)
    if not budget['fits']:
        return {**deepcopy(initial),'semantic_repair':{'protocol':PROTOCOL,'outcome':'not_run',
            'capacity':{'status':'NOT_RUN','reason':'complete_semantic_repair_request_budget','budget':budget}}}
    candidate=await extract(corrected,key+'-semantic')
    unchanged=repeats_failed_assertion(initial,candidate)
    preserved={assertion_signature(initial['draft'],a) for a in initial['draft']['assertions']
        if a['id'] not in {c['id'] for c in failed}}
    current={assertion_signature(candidate['draft'],a) for a in candidate['draft']['assertions']}
    accepted=candidate['review']['complete'] and not unchanged and preserved<=current
    selection=None
    if not accepted and failed and bounded is not None and not issues:
        from app.modules.knowledge.services.compilation_repair_selection import (
            INSTRUCTION,
            RepairSelectionCheck,
            apply_selection,
            check_selection,
            project_supported,
        )

        projected=project_supported(initial,candidate,assertion_signature)
        if projected is not None and not repeats_failed_assertion(initial,projected):
            request={**payload,'draft':projected['draft'],
                'repair_targets':corrected['candidate_correction']['rejected_assertions'],
                'repair_target_entities':initial['draft']['entities']}
            request.pop('candidate_correction',None)
            budget=planned_request_budget(RepairSelectionCheck,INSTRUCTION,request,transport)
            if budget['fits']:
                audit=RepairSelectionCheck.model_validate(await bounded(RepairSelectionCheck,INSTRUCTION,request))
                mapped=check_selection(initial,projected,audit,payload['evidence'])
                checked=apply_selection(projected,audit,payload,column_roles)
                accepted=mapped and checked['review']['complete']
                selection={'review':audit.model_dump(mode='json'),
                    'retained_assertion_ids':[a['id'] for a in checked['draft']['assertions']],
                    'quarantined_assertion_ids':[a['id'] for a in candidate['draft']['assertions']
                        if a['id'] not in {v['id'] for v in checked['draft']['assertions']}]}
            else:
                selection={'capacity':{'status':'NOT_RUN','reason':'complete_repair_selection_budget','budget':budget}}
    result=deepcopy(checked if accepted and selection else candidate if accepted else initial)
    result['semantic_repair']={'protocol':PROTOCOL,'outcome':'accepted' if accepted else 'unchanged' if unchanged else 'rejected',
        'initial':initial,**({'candidate':candidate} if not accepted or selection else {}),
        **({'selection':selection} if selection else {})}
    return result
