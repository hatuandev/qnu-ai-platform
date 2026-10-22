"""Literal temporal roles in user scope, independent of source publication authority."""
import re
from dataclasses import dataclass

_YEAR = r'(?:19|20)\d{2}(?:\s*[-–/]\s*(?:19|20)\d{2})?'
_TIME = re.compile(
    r'(?P<academic>năm học|academic year)|(?P<publication>năm ban hành|năm xuất bản|publication year)|'
    r'(?P<effective>năm hiệu lực|năm có hiệu lực|effective year)|'
    r'(?P<event>năm tổ chức|năm kỳ thi|event year)|'
    r'(?P<data>năm dữ liệu|năm số liệu|data year)|(?P<calendar>năm|year)', re.IGNORECASE)


@dataclass(frozen=True)
class UserTime:
    role: str
    value: str
    turn: int
    target: str = ''


def times(text: str, turn: int) -> list[UserTime]:
    from app.modules.rag.conversation_scope import named_scope

    result = []
    for marker in _TIME.finditer(text):
        match = re.match(r'\s+(' + _YEAR + r')\b', text[marker.end():])
        if match:
            owners = [m.value.casefold() for m in named_scope(text[:marker.start()], turn)
                      if m.field in {'program', 'program_code'}]
            result.append(UserTime(marker.lastgroup, re.sub(r'\s+', '', match[1]), turn, owners[-1] if owners else ''))
    return result


def temporal_errors(current: str, previous: list[str], rewritten: str, references=()) -> list[dict]:
    from app.modules.rag.conversation_scope import _active_mentions, _group_request

    active = {}
    for turn, question in [*enumerate(previous), (-1, current)]:
        found = times(question, turn)
        if not found:
            continue
        if all(t.role in {'academic', 'calendar'} for t in found):
            active.pop('academic', None)
            active.pop('calendar', None)
        for role in {t.role for t in found}:
            active[role] = {t.value for t in found if t.role == role}
    actual = {}
    for item in times(rewritten, -1):
        actual.setdefault(item.role, set()).add(item.value)
    if _group_request(current) or (previous and _group_request(previous[-1])):
        members = _active_mentions(current, previous, list(references)).get('program', [])
        members += _active_mentions(current, previous, list(references)).get('program_code', [])
        selected = {m.value.casefold() for m in members}
        if len(selected) > 1:
            expected = {}
            for turn, question in [*enumerate(previous), (-1, current)]:
                for item in times(question, turn):
                    if item.target in selected:
                        expected[(item.role, item.target)] = item.value
            if len({target for _, target in expected}) > 1:
                mapped = {(t.role, t.target):t.value for t in times(rewritten, -1)}
                for role in {role for role, _ in expected}:
                    shared = {value for (r, _), value in expected.items() if r == role}
                    if len(shared) == 1 and any(r == role and value in shared for (r, _), value in mapped.items()):
                        for key, value in expected.items():
                            if key[0] == role:
                                mapped.setdefault(key, value)
                if expected != mapped:
                    return [{'code':'TEMPORAL_TARGET_MISMATCH'}]
                active = {}
                for (role, _), value in expected.items():
                    active.setdefault(role, set()).add(value)
    if active != actual:
        return [{'code': 'TEMPORAL_ROLE_OR_VALUE_MISMATCH'}]
    return []
