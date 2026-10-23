"""Reconcile engine run fragments only against one complete native paragraph."""
import hashlib
import unicodedata
from collections import Counter
from copy import copy


def normalized(text: str) -> str:
    return ' '.join(unicodedata.normalize('NFC', text).split())


def reconcile_paragraphs(indexed: list, paragraphs: list) -> tuple[list, dict]:
    """No fuzzy matching, cross-paragraph joins or duplicate-text disambiguation.

    Original engine items remain untouched. The proof keeps their raw text and IDs;
    source note/numbering assignment remains with the existing native evidence pass.
    """
    native = {}
    for paragraph in paragraphs:
        text = normalized(paragraph.get('text', ''))
        if text and not paragraph.get('table') and not paragraph.get('numbering'):
            native.setdefault(text, []).append(paragraph)
    output, proofs, position = [], {}, 0
    starts = Counter(normalized(getattr(item, 'text', '')) for _, item, _ in indexed)
    while position < len(indexed):
        first, item, level = indexed[position]
        text = normalized(getattr(item, 'text', ''))
        candidates = []
        if (str(getattr(item, 'label', '')).lower() == 'text' and text
                and text not in native and starts[text] == 1):
            for full, matches in native.items():
                if len(matches) != 1 or not full.startswith(text) or full == text:
                    continue
                offset, fragments = 0, []
                for index, part, depth in indexed[position:position + 64]:
                    value = normalized(getattr(part, 'text', ''))
                    if (str(getattr(part, 'label', '')).lower() != 'text' or depth != level
                            or getattr(getattr(part, 'parent', None), 'cref', None) !=
                            getattr(getattr(item, 'parent', None), 'cref', None)
                            or not value or not full[offset:].startswith(value)):
                        break
                    fragments.append({'index': index, 'ref': getattr(part, 'self_ref', None),
                                      'text': part.text})
                    offset += len(value)
                    while offset < len(full) and full[offset].isspace():
                        offset += 1
                    if offset == len(full):
                        if len(fragments) > 1:
                            candidates.append((matches[0], fragments))
                        break
        if len(candidates) == 1:
            paragraph, fragments = candidates[0]
            replacement = copy(item)
            replacement.text = unicodedata.normalize('NFC', paragraph['text'])
            output.append((first, replacement, level))
            proofs[first] = {'version': 'docx-native-paragraph/v1', 'locator': paragraph['locator'],
                'sha256': hashlib.sha256(paragraph['text'].encode()).hexdigest(), 'fragments': fragments}
            position += len(fragments)
        else:
            output.append(indexed[position])
            position += 1
    return output, proofs
