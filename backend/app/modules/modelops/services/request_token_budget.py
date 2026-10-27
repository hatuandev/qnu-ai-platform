"""Capacity-bound request budgets; source text is never cropped or rewritten."""
from functools import lru_cache

from app.core.exceptions import AppException


@lru_cache(maxsize=3)
def tokenizer(name: str):
    import tiktoken

    try:
        return tiktoken.get_encoding(name)
    except (ValueError,OSError) as exc:
        raise AppException('Không nạp được tokenizer đã cấu hình.',code='MODEL_TOKENIZER_UNAVAILABLE',status_code=422) from exc


def input_tokens(messages: list[dict], encoding: str | None, overhead: int) -> tuple[int,str]:
    if encoding:
        # Ordinary encoding prevents document strings that resemble special
        # tokens from being counted as trusted message delimiters.
        count=sum(len(tokenizer(encoding).encode_ordinary(m['content'])) for m in messages)
        return count+overhead,'configured_tokenizer_with_measured_template_overhead'
    return sum(len(m['content'].encode('utf-8')) for m in messages)+1024,'utf8_upper_bound_with_framing'


def automatic_budget(messages: list[dict], capacity: dict, minimum_output: int = 1, *, feedback_reserve: int = 0) -> dict:
    roles=capacity.get('calibrated_roles')
    if roles and [m['role'] for m in messages]!=roles:
        raise AppException('Template chưa được đo cho cấu trúc hội thoại này.',
            code='MODEL_TOKEN_ENVELOPE_UNVERIFIED',status_code=422)
    context=capacity['context_window_tokens']
    count,method=input_tokens(messages,capacity.get('tokenizer_encoding'),capacity.get('chat_overhead_tokens',0))
    available=min(capacity.get('max_output_tokens') or context,context-count-feedback_reserve)
    output=max(0,available)
    return {'method':method,'input_upper_bound':count,'reserved_output_tokens':output,
        'minimum_output_tokens':minimum_output,'feedback_reserve':feedback_reserve,
        'total_reserved':count+output+feedback_reserve,'workflow_limit':context,
        'fits':output>=minimum_output,'automatic_output_budget':True,
        'capacity_basis':capacity.get('basis'),'capacity_source':capacity.get('capacity_source'),
        'capacity_verified_by_inference':capacity.get('capacity_verified_by_inference',False)}
