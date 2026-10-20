"""Read OOXML numbering as source evidence, independent of Markdown rendering."""
import re
from collections import defaultdict

from lxml import etree

NS = {'w': 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'}
W = '{' + NS['w'] + '}'
MARKER = re.compile(r'^\s*((?:\d+[.)]|[A-Za-zĐđ]+[.)]|[-*•]))\s+')


def _read(archive, name):
    return etree.fromstring(archive.read(name), etree.XMLParser(resolve_entities=False, no_network=True))


def _value(node, name, default=None):
    found = node.find('w:' + name, NS) if node is not None else None
    return found.get(W + 'val', default) if found is not None else default


def _roman(value):
    result = ''
    for number, digits in [(1000, 'M'), (900, 'CM'), (500, 'D'), (400, 'CD'), (100, 'C'), (90, 'XC'), (50, 'L'), (40, 'XL'), (10, 'X'), (9, 'IX'), (5, 'V'), (4, 'IV'), (1, 'I')]:
        while value >= number:
            result += digits
            value -= number
    return result


def _format(value, kind):
    if kind in {'decimal', 'decimalZero'}:
        return str(value).zfill(2) if kind == 'decimalZero' else str(value)
    if kind in {'lowerLetter', 'upperLetter'} and value > 0:
        result = ''
        while value:
            value, rem = divmod(value - 1, 26)
            result = chr(65 + rem) + result
        return result.lower() if kind == 'lowerLetter' else result
    if kind in {'lowerRoman', 'upperRoman'} and 0 < value < 4000:
        result = _roman(value)
        return result.lower() if kind == 'lowerRoman' else result
    return None


def _number_pr(paragraph, styles):
    props = paragraph.find('w:pPr', NS)
    direct = props.find('w:numPr', NS) if props is not None else None
    style, seen, inherited = _value(props, 'pStyle'), set(), None
    while style and style not in seen and style in styles:
        seen.add(style)
        node = styles[style]
        inherited = node.find('w:pPr/w:numPr', NS)
        if inherited is not None:
            break
        style = _value(node, 'basedOn')
    num_id = _value(direct, 'numId', _value(inherited, 'numId'))
    level = _value(direct, 'ilvl', _value(inherited, 'ilvl', '0'))
    return num_id, int(level) if str(level).isdigit() else 0


def numbering_evidence(archive, paragraphs):
    if 'word/numbering.xml' not in archive.namelist():
        return {}
    root = _read(archive, 'word/numbering.xml')
    abstracts = {n.get(W + 'abstractNumId'): n for n in root.findall('w:abstractNum', NS)}
    nums = {n.get(W + 'numId'): n for n in root.findall('w:num', NS)}
    styles = {n.get(W + 'styleId'): n for n in _read(archive, 'word/styles.xml')} if 'word/styles.xml' in archive.namelist() else {}
    counters, result = defaultdict(dict), {}
    for index, paragraph in enumerate(paragraphs, 1):
        num_id, level = _number_pr(paragraph, styles)
        if num_id in {None, '0'} or num_id not in nums:
            continue
        num = nums[num_id]
        abstract_id = _value(num, 'abstractNumId')
        abstract = abstracts.get(abstract_id)
        if abstract is None:
            continue
        levels = {int(n.get(W + 'ilvl')): n for n in abstract.findall('w:lvl', NS)}
        overrides = {int(n.get(W + 'ilvl')): n for n in num.findall('w:lvlOverride', NS)}
        override = overrides.get(level)
        effective = override.find('w:lvl', NS) if override is not None else None
        node = effective if effective is not None else levels.get(level)
        if node is None:
            continue
        start = int(_value(override, 'startOverride', _value(node, 'start', '1')))
        current = counters[num_id]
        current[level] = current.get(level, start - 1) + 1
        for deeper in list(current):
            if deeper > level and _value(levels.get(deeper), 'lvlRestart', '1') != '0':
                del current[deeper]
        kind, pattern = _value(node, 'numFmt', 'decimal'), _value(node, 'lvlText', '')
        missing = []

        def replace(match, current=current, levels=levels, missing=missing):
            target = int(match[1]) - 1
            value = _format(current.get(target, 1), _value(levels.get(target), 'numFmt', 'decimal'))
            if value is None:
                missing.append(target)
            return value if value is not None else match[0]

        marker = re.sub(r'%(\d+)', replace, pattern)
        result[f'word/document.xml#p{index}'] = {'num_id': num_id, 'abstract_num_id': abstract_id,
            'level': level, 'format': kind, 'start': start, 'value': current[level], 'pattern': pattern,
            'marker': marker, 'status': 'unresolved' if missing or not marker else 'source_defined'}
    return result


def list_key(text):
    return ' '.join(MARKER.sub('', text, count=1).split())


def list_item_evidence(indexed, paragraphs):
    """Align equal source occurrences in order only when both inventories agree."""
    source, items, result = defaultdict(list), defaultdict(list), {}
    for p in paragraphs:
        if not p.get('table') and (p.get('numbering') or MARKER.match(p['text'])):
            source[list_key(p['text'])].append(p)
    for index, item, _ in indexed:
        label = str(getattr(item, 'label', ''))
        if label.rsplit('.', 1)[-1].casefold() == 'list_item':
            items[list_key(getattr(item, 'text', ''))].append(index)
    for key, indices in items.items():
        if len(indices) == len(source[key]):
            result.update(zip(indices, source[key], strict=True))
    return result


def render_list_items(items):
    lines, widths, previous_numbers = [], {}, {}
    base = min((item['level'] for item in items), default=0)
    for item in items:
        level, marker = item['level'] - base, item['marker']
        for deeper in list(widths):
            if deeper > level:
                del widths[deeper]
        indent = sum(widths.get(n, 2) for n in range(level))
        prefix = marker if re.fullmatch(r'\d+[.)]', marker or '') else '-'
        if re.fullmatch(r'\d+[.)]', prefix):
            number = int(prefix[:-1])
            if level in previous_numbers and number != previous_numbers[level] + 1:
                # CommonMark ignores later ordinal values within one list.
                # A neutral block boundary preserves an explicit source restart.
                lines.extend(['', ' ' * indent + '<!-- source-list-restart -->', ''])
            previous_numbers[level] = number
        for deeper in list(previous_numbers):
            if deeper > level:
                del previous_numbers[deeper]
        label = '' if prefix == marker or marker in {'-', '*', '•', ''} else '**' + marker + '** '
        widths[level] = len(prefix) + 1
        body = item['text'].splitlines() or ['']
        lines.append(' ' * indent + prefix + ' ' + label + body[0])
        lines.extend(' ' * (indent + len(prefix) + 1) + line for line in body[1:])
    return '\n'.join(lines)
