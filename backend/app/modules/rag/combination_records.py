"""Source-owned records and tuple predicates; no hand-maintained program catalog."""

import html
import re
from dataclasses import dataclass

from app.modules.knowledge.facts import detect_column_role
from app.modules.knowledge.services.table_context import extract_context_tables, row_identities
from app.modules.rag.evidence_schemas import EvidenceBlock
from app.modules.rag.facts import count_subject_matches
from app.modules.rag.query_router import query_classifier


@dataclass
class CombinationRecord:
    code: str
    name: str
    combinations: list[str]
    block: EvidenceBlock
    years: tuple[int, ...] = ()


def clean(value: str) -> str:
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<br\s*/?>", " ", value, flags=re.IGNORECASE))).strip(" *_`")


def matching_tuples(value: str, subjects: list[str]) -> list[str]:
    """All requested subjects must occur in one original delimited tuple."""
    groups = re.findall(r"\([^()]+\)", html.unescape(value))
    if not groups:
        groups = [part.strip() for part in re.split(r"[;\n|]", html.unescape(value)) if part.strip()]
    return list(dict.fromkeys(clean(group) for group in groups
        if count_subject_matches(group, subjects) == len(set(subjects))))


def query_subjects(question: str) -> list[str]:
    """Use contiguous syntactic subject runs, not matches elsewhere in a sentence."""
    spans = sorted({(match.start(), match.end(), canonical)
        for pattern, canonical in query_classifier.SUBJECT_PATTERNS for match in pattern.finditer(question.casefold())},
        key=lambda span: (span[0], -(span[1] - span[0])))
    spans = [span for span in spans if not any(other != span and other[0] <= span[0]
             and other[1] >= span[1] and other[1] - other[0] > span[1] - span[0] for other in spans)]
    runs = []
    for span in spans:
        if not runs or not re.fullmatch(r"[\s,;()/–—-]*(?:và\s*)?", question.casefold()[runs[-1][-1][1]:span[0]]):
            runs.append([])
        runs[-1].append(span)
    best = max(runs, key=len, default=[])
    return list(dict.fromkeys(span[2] for span in best))


def cell_combinations(cells: list[tuple[str, str]], subjects: list[str]) -> dict[tuple[int, ...], list[str]]:
    """A tuple inherits only its own column's year, never a sibling column's year."""
    groups = {}
    for label, value in cells:
        role, year = detect_column_role(label)
        if role != "combos":
            continue
        matches = matching_tuples(value, subjects)
        if matches:
            key = (int(year),) if year else ()
            groups[key] = list(dict.fromkeys([*groups.get(key, []), *matches]))
    return groups


def records_from_block(block: EvidenceBlock, subjects: list[str]) -> list[CombinationRecord]:
    if block.is_container:
        return []
    if block.origin == "reviewed_fact":
        cells = block.fact_context.get("cells", [])
        code = next((clean(cell["value"]) for cell in cells
                     if detect_column_role(cell["attribute"])[0] == "code"), block.fact_context.get("entity_code") or "")
        groups = cell_combinations([(cell["attribute"], cell["value"]) for cell in cells], subjects)
        return [CombinationRecord(code, clean(block.fact_context.get("entity_name", "")), combos, block, years)
                for years, combos in groups.items()]
    if block.text.lstrip().startswith("|"):
        tables = extract_context_tables(block.header_context + "\n" + block.text, 1)
        records = []
        for table in tables:
            combo_cols = [i for i, label in enumerate(table["headers"]) if detect_column_role(label)[0] == "combos"]
            for row in table["rows"]:
                if len(row) != len(table["headers"]):
                    continue
                for identity, end, name, code in row_identities(row, table):
                    own_cols = [i for i in combo_cols if identity < i < end]
                    groups = cell_combinations([(table["headers"][i], row[i]) for i in own_cols], subjects)
                    for years, combos in groups.items():
                        records.append(CombinationRecord(code or "", clean(name), combos, block, years))
        return records
    # A numbered repeated record: bold identity, a labelled bold code, then fields.
    # Field labels are resolved through the existing schema, not a new vocabulary.
    match = re.match(r"\s*\d+[.)]\s+\*\*(.+?)\*\*\s*[—–-]\s*([^:\n]+):\s*\*\*([^*]+)\*\*(.*)", block.text, re.DOTALL)
    if not match or detect_column_role(match[2])[0] != "code":
        return []
    fields = re.split(r"(?<=[.;])\s+(?=[^:;()\n]{2,80}:)", match[4])
    values = [field.split(":", 1)[1] for field in fields
              if ":" in field and detect_column_role(field.split(":", 1)[0])[0] == "combos"]
    combos = list(dict.fromkeys(combo for value in values for combo in matching_tuples(value, subjects)))
    return [CombinationRecord(clean(match[3]), clean(match[1]), combos, block)] if combos else []
