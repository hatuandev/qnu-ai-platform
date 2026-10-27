"""Explicit request-local span identities and eligible fields, never semantic approval."""
from app.modules.knowledge.services.compilation_grounding import (
    extraction_choices,
    heading_spans,
    offered_spans,
    prose_primary,
)

PROTOCOL='explicit-source-span-id-offsets-and-eligible-roles/v2-prose-without-column'


def source_span_menu(payload: dict, handles: dict[str,str], *, headings: bool=False) -> dict:
    choices=heading_spans(payload) if headings else offered_spans(payload)
    if headings:
        fields={'heading':set(choices)}
    else:
        subjects,metrics,scalars=extraction_choices(payload,choices)
        labels={sid for sid,value in choices.items() if len(value['literal'])<=200}
        fields={'subject':set(subjects),'metric':set(metrics),'column':set() if prose_primary(payload) else labels,'scalar':set(scalars),
                'limitation':set(scalars),'unit':labels,'scope.anchor':labels}
    return {sid:{'span_id':sid,'evidence_id':handles[value['evidence_id']],
        'literal':value['literal'],'start':value['start'],'end':value['end'],
        'allowed_roles':[role for role,eligible in fields.items() if sid in eligible]}
        for sid,value in choices.items()}


def span_error_feedback(error: dict, choices: dict) -> dict:
    location=error['loc']
    if not location or location[-1]!='span_id':
        return {}
    role='scope.anchor' if len(location)>1 and location[-2]=='anchor' else location[-2] if len(location)>1 else None
    supplied=error.get('input')
    offered=choices.get(supplied) if isinstance(supplied,str) else None
    if offered is None:
        return {'required_span_role':role,'unoffered_span_id':True}
    return {'required_span_role':role,'supplied_span_id':supplied,
            'offered_span_roles':offered['allowed_roles']}
