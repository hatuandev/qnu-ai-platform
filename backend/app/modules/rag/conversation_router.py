"""One bounded routing step before evidence RAG; social replies contain no document facts."""
import hashlib
import time

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AppException
from app.modules.rag.intent_contracts import IntentDecision
from app.modules.rag.intent_debug import intent_debug_enabled
from app.modules.rag.intent_rules import (
    depends_on_context,
    has_social_prefix,
    is_meta,
    normalize_dialogue,
    social_kind,
    social_remainder,
    useful_user_questions,
)
from app.modules.rag.schemas import AskRequest, AskResponse


def fast_reply(req: AskRequest) -> tuple[IntentDecision, str] | None:
    kind = social_kind(req.question)
    rest = social_remainder(req.question)
    if kind or is_meta(req.question) or is_meta(rest) or (rest.startswith('ban ') and is_meta(rest[4:])):
        identity = req._assistant_identity
        name = identity.get('name') or 'trợ lý AI'
        topics = identity.get('allowed_topics') or []
        introduction = f'Mình là {name}.'
        scope = (' Mình có thể hỗ trợ tra cứu: ' + ', '.join(topics) + '.') if topics else ' Mình có thể hỗ trợ tra cứu thông tin trong kho tri thức được phép sử dụng.'
        answer = {'greeting': f'Xin chào! {introduction}{scope} Bạn muốn tìm hiểu nội dung nào?',
            'thanks': 'Rất vui được hỗ trợ bạn! Bạn cứ hỏi tiếp nếu cần nhé.',
            'farewell': 'Tạm biệt bạn! Hẹn gặp lại.'}.get(kind, introduction + scope)
        return IntentDecision(intent='SOCIAL' if kind else 'ASSISTANT_META', requires_rag=False,
            classification_method='rule', reason_code='WHOLE_MESSAGE_SOCIAL' if kind else 'CONFIGURED_ASSISTANT_META'), answer
    return None


async def route_turn(db: AsyncSession, req: AskRequest) -> tuple[AskRequest, dict | None, AskResponse | None]:
    from app.modules.rag.conversation_resolution import resolve_followup

    started = time.perf_counter()
    req._intent_trace = {'original_message': req.question, 'router_model_calls': 0}
    direct = fast_reply(req)
    if direct:
        decision, answer = direct
        req._intent_trace.update(decision.model_dump())
        req._intent_trace['router_latency_ms'] = round((time.perf_counter() - started) * 1000, 2)
        return req, None, AskResponse(status='answered', answer=answer)
    mixed = has_social_prefix(req.question)
    dependent = depends_on_context(req.question)
    previous = useful_user_questions(req.history)
    value = social_remainder(req.question) or normalize_dialogue(req.question)
    unclear = value in {'tu van giup toi', 'tu van giup minh', 'nganh nao tot', 'giup toi', 'help', 'help me'}
    unclear = unclear or (value.startswith(('cho ', 'hay ', 'giup ')) and value.endswith('gi do'))
    if unclear or (dependent and not previous):
        decision = IntentDecision(intent='CLARIFICATION', requires_rag=False, requires_context=dependent,
            classification_method='rule', reason_code='MISSING_USER_SCOPE')
        effective, resolution = req, {'mode': 'clarify', 'reason': decision.reason_code}
    else:
        method = 'rule'
        try:
            req._intent_trace['planning'] = True
            if dependent:
                effective, resolution = await resolve_followup(db, req, hybrid=True)
                method = 'model'
            else:
                effective, resolution = await resolve_followup(db, req)
                if resolution or req._intent_trace.get('router_model_calls'):
                    method = 'model'
        except (TimeoutError, AppException) as exc:
            if isinstance(exc, AppException) and exc.status_code not in {429, 502, 503, 504}:
                raise
            effective, resolution = req, {'mode': 'clarify', 'reason': 'ROUTER_UNAVAILABLE'}
            method = 'fallback'
            req._intent_trace['error_code'] = exc.code if isinstance(exc, AppException) else 'ROUTER_TIMEOUT'
        finally:
            req._intent_trace.pop('planning', None)
        clarify = resolution and resolution.get('mode') == 'clarify'
        intent = 'CLARIFICATION' if clarify else 'MIXED' if mixed else 'KNOWLEDGE_FOLLOWUP' if resolution else 'KNOWLEDGE'
        decision = IntentDecision(intent=intent, requires_rag=not bool(clarify), requires_context=dependent or bool(resolution),
            classification_method=method, reason_code=(resolution or {}).get('reason', 'CONTEXT_RESOLVED' if resolution else 'KNOWLEDGE_REQUEST'))
    req._intent_trace.update(decision.model_dump(exclude={'confidence'}))
    req._intent_trace.update(rewritten_query=effective.question,
        router_latency_ms=round((time.perf_counter() - started) * 1000, 2))
    effective._intent_trace = req._intent_trace
    return effective, resolution, None


def finish_routing(req: AskRequest, response: AskResponse) -> AskResponse:
    if intent_debug_enabled() and req._intent_trace:
        trace = {**req._intent_trace, 'rag_invoked': req._intent_trace.get('requires_rag', False),
            'total_latency_ms': response.latency_ms,
            'retrieval_result_count': (response.retrieval_diagnostics or {}).get('fused_count'),
            'conversation_hash': hashlib.sha256((req.conversation_id or '').encode()).hexdigest()[:12]}
        response.retrieval_diagnostics = {**(response.retrieval_diagnostics or {}), 'intent_routing': trace}
    return response
