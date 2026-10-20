"""Conservative whole-message conversational rules; never match a social substring."""
import re
import unicodedata


def normalize_dialogue(text: str) -> str:
    folded = unicodedata.normalize('NFD', text.casefold()).replace('đ', 'd')
    folded = ''.join(c for c in folded if not unicodedata.combining(c))
    return ' '.join(re.sub(r'[^\w\s]', ' ', folded).split())


_POLITE = r'(?: (?:ban|anh|chi|em|thay|co|minh|a|oi|nhe|nha|nhieu|rat nhieu|nhieu lam|lam))*'
_SOCIAL_BASES = {
    'greeting': r'(?:(?:xin )?chao(?: buoi (?:sang|chieu|toi))?|hello|hi|hey|good morning|good afternoon|good evening)',
    'thanks': r'(?:cam on|xin cam on|thank you|thanks|thanks a lot)',
    'farewell': r'(?:tam biet|chao tam biet|hen gap lai|bye|bye bye|goodbye|see you)',
}
_SOCIAL = {kind: re.compile(base + _POLITE) for kind, base in _SOCIAL_BASES.items()}
_META = re.compile(r'(?:ban la ai|ban ten (?:la )?gi|ban (?:co the )?(?:giup|ho tro)(?: duoc)? (?:gi|nhung gi)|'
                   r'ban co the lam (?:gi|nhung gi)|who are you|what can you do|'
                   r'ban co the (?:tu van|ho tro) [a-z ]{2,70} (?:khong|duoc khong))')
_DEPENDENT = re.compile(r'^(?:con |vay |khong toi hoi |khong minh hoi |what about )|'
                        r'\b(?:(?:nganh|truong|chuong trinh|doi tuong|nam|cai) (?:do|nay|truoc)|'
                        r'that program|those|same program|instead)\b')


def social_kind(text: str) -> str | None:
    value = normalize_dialogue(text)
    return next((kind for kind, rule in _SOCIAL.items() if rule.fullmatch(value)), None)


def is_meta(text: str) -> bool:
    return bool(_META.fullmatch(normalize_dialogue(text)))


def has_social_prefix(text: str) -> bool:
    value = normalize_dialogue(text)
    return bool(social_remainder(value)) and social_kind(text) is None


def social_remainder(text: str) -> str:
    value = normalize_dialogue(text)
    for base in _SOCIAL_BASES.values():
        match = re.match(base, value)
        if match and match.end() < len(value) and value[match.end()] == ' ':
            return value[match.end():].strip()
    return ''


def depends_on_context(text: str) -> bool:
    rest = social_remainder(text)
    value = rest.removeprefix('ban ') if rest else normalize_dialogue(text)
    return bool(_DEPENDENT.search(value)) or value in {'co', 'khong', 'ok', 'oke', 'yes', 'no', 'duoc'}


def useful_user_questions(history: list[dict] | None, limit: int = 8) -> list[str]:
    return [turn['content'] for turn in history or [] if turn.get('role') == 'user'
            and turn.get('content') and not social_kind(turn['content']) and not is_meta(turn['content'])][-limit:]
