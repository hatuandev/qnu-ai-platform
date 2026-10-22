"""Conservative, extractive scope checks; user quotations never grant source access."""
import re
from dataclasses import dataclass

from app.modules.rag.intent_contracts import ContextReferent

# Language constructions delimit user-named scope, never a catalog of source entities.
_MARKERS = re.compile(
    r'\b(?:(?P<program>ngành|chương trình|program|major)|'
    r'\b(?P<institution>trường|cơ quan|institution|university)|'
    r'\b(?P<source>tài liệu|văn bản|document|file)|'
    r'\b(?P<source_locator>bảng|table|điều|article|mục|section|hình|figure)|'
    r'\b(?P<program_code>mã|code)|'
    r'(?P<boundary>năm học|năm|year|in|tại|trong|from|for|at|ban hành|hiệu lực))\b', re.IGNORECASE)
_END = re.compile(
    r'[,;:?!\n]|\.(?:\s|$)|\b(?:là|bao nhiêu|mấy|thì|có|được|thuộc|'
    r'chỉ|không|nếu|ngoại trừ|except|excluding|without|only|if|unless)\b', re.IGNORECASE)
_DEICTIC = re.compile(r'^(?:đó|này|ấy|trước|kia|that|this|same|those)\b', re.IGNORECASE)
_PREDICATE = re.compile(
    r'\b(?:nếu|khi|miễn là|với điều kiện|đối với|áp dụng cho|trừ|ngoại trừ|loại trừ|'
    r'không|chẳng|chớ|đừng|chỉ(?! tiêu\b)|tối thiểu|tối đa|lớn hơn|nhỏ hơn|'
    r'từ ngày|đến ngày|trước ngày|sau ngày|if|when|unless|except|excluding|without|'
    r'only|not|subject to|provided|at least|less than|before|after)\b', re.IGNORECASE)
_QUOTED_EDIT = re.compile(
    r'(?:^|(?<=[;.!?\n]))\s*(?P<verb>bỏ|xóa|gỡ|thay|remove|replace)\s+(?:điều kiện|bộ lọc|condition|filter)\s+'
    r'["“](?P<old>[^"”\n]+)["”]'
    r'(?:\s+(?:bằng|with)\s+["“](?P<new>[^"”\n]+)["”])?', re.IGNORECASE)
_BOOLEAN = re.compile(r'\b(?:và|hoặc|hay|and|or)\b', re.IGNORECASE)


def _key(text: str) -> str:
    return ' '.join(re.findall(r'\w+|[^\w\s]', text.casefold())).strip()


def _contains(text: str, value: str) -> bool:
    return bool(re.search(r'(?<!\w)' + re.escape(_key(value)) + r'(?!\w)', _key(text)))


@dataclass(frozen=True)
class ScopeMention:
    field: str
    value: str
    turn: int
    source: str = ''


def named_scope(text: str, turn: int) -> list[ScopeMention]:
    """Keep complete delimited names, including punctuation in codes and quoted titles."""
    quoted_spans = [m.span() for m in re.finditer(r'["“][^"”]+["”]|https?://\S+', text, re.IGNORECASE)]
    markers = [m for m in _MARKERS.finditer(text)
               if not any(start < m.start() < end for start, end in quoted_spans)]
    mentions = []
    source = ''
    for index, marker in enumerate(markers):
        field = marker.lastgroup
        if field == 'boundary':
            continue
        end = markers[index + 1].start() if index + 1 < len(markers) else len(text)
        tail = text[marker.end():end].strip()
        quoted = re.match(r'^["“]([^"”]+)["”]', tail)
        url = re.match(r'https?://\S+', tail, re.IGNORECASE)
        value = (quoted[1] if quoted else url[0].rstrip('.,;:?!') if url
                 else _END.split(tail, maxsplit=1)[0].strip(' ."“”'))
        value = re.sub(r'\s+(?:và|hoặc|and|or|với|with)$', '', value, flags=re.IGNORECASE)
        if not value or _DEICTIC.match(value):
            continue
        if field == 'source_locator':
            if not quoted:
                value = re.split(r'\s+(?:về|about|cho|for)\s+', value, maxsplit=1, flags=re.IGNORECASE)[0]
            value = marker[0] + ' ' + value
        if field == 'source':
            source = value
        mentions.append(ScopeMention(field, value, turn, source if field == 'source_locator' else ''))
    return mentions


def _set_mentions(text: str, turn: int, references: list[ContextReferent]) -> list[ScopeMention]:
    result = []
    for mention in named_scope(text, turn):
        parts = re.split(r'\s+(?:và|and)\s+', mention.value, flags=re.IGNORECASE)
        if _group_request(text) and len(parts) > 1 and all(any(
                r.field == mention.field and _key(r.value) == _key(part) for r in references) for part in parts):
            result.extend(ScopeMention(mention.field, part, turn, mention.source) for part in parts)
        else:
            result.append(mention)
    return result


def _active_mentions(current: str, previous: list[str], references: list[ContextReferent]) -> dict[str, list[ScopeMention]]:
    active = {}
    for turn, question in [*enumerate(previous), (-1, current)]:
        mentions = _set_mentions(question, turn, references)
        if any(m.field == 'program' and 'program' in active
               and _key(m.value) not in {_key(old.value) for old in active['program']} for m in mentions):
            active.pop('program_code', None)  # A new named subject cannot inherit an old subject's code.
        if any(m.field == 'source' and 'source' in active
               and _key(m.value) not in {_key(old.value) for old in active['source']} for m in mentions):
            active.pop('source_locator', None)
        for field in {m.field for m in mentions}:
            active[field] = [m for m in mentions if m.field == field]
    # An explicit comparison of the two preceding subjects can restore both;
    # an ordinary followup always inherits only the last explicit set.
    for field, noun in [('program', 'ngành|chương trình|programs?|majors?'),
                        ('source_locator', 'bảng|tables?'), ('institution', 'trường|institutions?'),
                        ('source', 'tài liệu|documents?')]:
        if _group_request(current) and re.search(r'\b(?:hai|both|two)\s+(?:' + noun + r')\b', current, re.IGNORECASE):
            candidates = [m for turn, text in enumerate(previous) for m in _set_mentions(text, turn, references) if m.field == field]
            distinct = {_key(m.value): m for m in candidates}
            if len(distinct) == 2:
                active[field] = list(distinct.values())
    return active


def _group_request(text: str) -> bool:
    return bool(re.search(r'\b(?:so sánh|đối chiếu|compare|comparison|versus|liệt kê|list|cả hai|both)\b', text, re.IGNORECASE))


def referent_set_errors(references: list[ContextReferent], current: str, previous: list[str]) -> list[dict]:
    active = _active_mentions(constraint_query_text(current), [constraint_query_text(q) for q in previous], references)
    errors = []
    for field in {ref.field for ref in references}:
        refs = [r for r in references if r.field == field]
        allowed = active.get(field, [])
        if len({r.value for r in refs}) > 1 and field not in active and not _group_request(current):
            errors.append({'field': field, 'code': 'CONFLICTING_FIELD_VALUES'})
        for ref in refs:
            if allowed and not any(_contains(ref.value, m.value) and
                    (ref.source_turn == m.turn or m.turn == -1) for m in allowed):
                errors.append({'field': field, 'code': 'SUPERSEDED_USER_SCOPE'})
    return errors


def named_scope_errors(references: list[ContextReferent], current: str, previous: list[str],
                       rewritten: str, *, require_proof: bool = True) -> list[dict]:
    active = _active_mentions(current, previous, references)
    errors = []
    for field, members in active.items():
        for mention in members:
            if not _contains(rewritten, mention.value):
                errors.append({'field': field, 'code': 'NAMED_SCOPE_NOT_PRESERVED'})
            elif require_proof and mention.turn != -1 and not any(ref.field == field and ref.source_turn == mention.turn
                    and _contains(ref.value, mention.value) for ref in references):
                errors.append({'field': field, 'code': 'MISSING_SCOPE_PROOF'})
    for mention in _set_mentions(rewritten, -1, references):
        expected = active.get(mention.field, [])
        if not any(_key(mention.value) == _key(m.value) and _key(mention.source) == _key(m.source) for m in expected):
            errors.append({'field': mention.field, 'code': 'UNSUPPORTED_NAMED_SCOPE'})
    return errors


def _conditions(text: str) -> list[str]:
    text = re.sub(r'^\s*không\s*[,;:.]?\s*(?:tôi|mình|em)\s+(?:muốn\s+)?hỏi\s*', '', text, flags=re.IGNORECASE)
    titles = [m.span() for m in re.finditer(
        r'\b(?:tài liệu|văn bản|document|file|ngành|program|trường|institution)\s+["“][^"”]+["”]',
        text, re.IGNORECASE)]
    result = []
    for match in _PREDICATE.finditer(text):
        if any(start <= match.start() < end for start, end in titles):
            continue
        tail = re.split(r'[?!\n]|\.(?:\s|$)|\bthì\b', text[match.start():], maxsplit=1, flags=re.IGNORECASE)[0]
        value = tail.strip(' ,.:')
        if value:
            result.append(value)
    return result


def _history_conditions(previous: list[str]) -> list[str]:
    """Keep the supplied user chain conservatively; a model cannot select away a filter."""
    conditions = []
    for question in previous:
        conditions, remaining, _ = _apply_edits(conditions, question)
        conditions.extend(_conditions(remaining))
    return list(dict.fromkeys(conditions))


def _apply_edits(conditions: list[str], current: str) -> tuple[list[str], str, list[dict]]:
    """Only a literal user command can remove/replace a complete inherited clause."""
    kept = list(conditions)
    errors = []
    for edit in _QUOTED_EDIT.finditer(current):
        old = edit['old']
        if not any(_key(old) == _key(c) for c in kept):
            errors.append({'code': 'CONDITION_EDIT_UNPROVEN'})
            continue
        replacing = edit['verb'].casefold() in {'thay', 'replace'}
        if replacing != bool(edit['new']):
            errors.append({'code': 'CONDITION_EDIT_UNPROVEN'})
            continue
        kept = [c for c in kept if not _contains(old, c)]
        if replacing:
            kept.append(edit['new'])
    return kept, _QUOTED_EDIT.sub('', current), errors


def condition_errors(current: str, previous: list[str], rewritten: str) -> list[dict]:
    conditions, remaining, errors = _apply_edits(_history_conditions(previous), current)
    conditions.extend(_conditions(remaining))
    if any(not _contains(rewritten, condition) for condition in conditions):
        errors.append({'code': 'CONDITION_NOT_PRESERVED'})
    if not conditions and not _conditions(rewritten) and _group_request(current):
        return errors  # Named-set coverage separately proves every comparison member.
    errors.extend(_condition_coverage(conditions, rewritten, [*previous, remaining]))
    return errors


def _condition_coverage(conditions: list[str], rewritten: str, originals: list[str]) -> list[dict]:
    """Cover predicate starts and operators, including operators across separators."""
    query = _key(rewritten)
    spans = [match.span() for condition in conditions for match in re.finditer(
        r'(?<!\w)' + re.escape(_key(condition)) + r'(?!\w)', query)]
    covered = lambda offset: any(start <= offset < end for start, end in spans)
    for condition in _conditions(rewritten):
        if not covered(query.find(_key(condition))):
            return [{'code': 'UNSUPPORTED_CONDITION'}]
    # Operators in the main request also need their original literal neighbours.
    heads = []
    for original in originals:
        predicate = _conditions(original)
        heads.append(_key(original).split(_key(predicate[0]))[0] if predicate else _key(original))
    for operator in _BOOLEAN.finditer(query):
        if covered(operator.start()):
            continue
        left = re.findall(r'\w+', query[:operator.start()])[-1:]
        right = re.findall(r'\w+', query[operator.end():])[:1]
        phrase = ' '.join([*left, operator[0], *right])
        if not left or not right or not any(_contains(head, phrase) for head in heads):
            return [{'code': 'UNSUPPORTED_BOOLEAN_SCOPE'}]
    return []


def contextual_scope_errors(references: list[ContextReferent], current: str,
                            previous: list[str], rewritten: str, *, require_proof: bool = True) -> list[dict]:
    """Diagnostics contain role/code only; no query, quotation or source credential."""
    return (named_scope_errors(references, constraint_query_text(current),
                              [constraint_query_text(q) for q in previous], rewritten, require_proof=require_proof)
            + condition_errors(current, previous, rewritten))


def constraint_query_text(current: str) -> str:
    """Quoted old operands of an explicit edit are not new query values."""
    return _QUOTED_EDIT.sub(lambda match: match['new'] or '', current)
