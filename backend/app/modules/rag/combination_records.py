"""Source-owned records and tuple predicates; no hand-maintained program catalog."""

import html
import re
from dataclasses import dataclass

from app.modules.knowledge.facts import detect_column_role
from app.modules.knowledge.services.table_context import extract_context_tables, row_identities
from app.modules.rag.evidence_schemas import EvidenceBlock
from app.modules.rag.facts import count_subject_matches


@dataclass
class CombinationRecord:
    code: str
    name: str
    combinations: list[str]
    block: EvidenceBlock


def clean(value: str) -> str:
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<br\s*/?>", " ", value, flags=re.I))).strip(" *_`")


def matching_tuples(value: str, subjects: list[str]) -> list[str]:
    """All requested subjects must occur in one original delimited tuple."""
    groups = re.findall(r"\([^()]+\)", html.unescape(value))
    if not groups:
        groups = [part.strip() for part in re.split(r"[;\n|]", html.unescape(value)) if part.strip()]
    return list(dict.fromkeys(clean(group) for group in groups
        if count_subject_matches(group, subjects) == len(set(subjects))))


def records_from_block(block: EvidenceBlock, subjects: list[str]) -> list[CombinationRecord]:
    if block.is_container:
        return []
    if block.origin == "reviewed_fact":
        cells = block.fact_context.get("cells", [])
        values = [cell["value"] for cell in cells if detect_column_role(cell["attribute"])[0] == "combos"]
        combos = list(dict.fromkeys(combo for value in values for combo in matching_tuples(value, subjects)))
        code = next((clean(cell["value"]) for cell in cells
                     if detect_column_role(cell["attribute"])[0] == "code"), "")
        return [CombinationRecord(code, clean(block.fact_context.get("entity_name", "")), combos, block)] if combos else []
    if block.text.lstrip().startswith("|"):
        tables = extract_context_tables(block.header_context + "\n" + block.text, 1)
        records = []
        for table in tables:
            combo_cols = [i for i, label in enumerate(table["headers"]) if detect_column_role(label)[0] == "combos"]
            for row in table["rows"]:
                if len(row) != len(table["headers"]):
                    continue
                for _, _, name, code in row_identities(row, table):
                    combos = list(dict.fromkeys(combo for i in combo_cols for combo in matching_tuples(row[i], subjects)))
                    if combos:
                        records.append(CombinationRecord(code or "", clean(name), combos, block))
        return records
    # A numbered repeated record: bold identity, a labelled bold code, then fields.
    # Field labels are resolved through the existing schema, not a new vocabulary.
    match = re.match(r"\s*\d+[.)]\s+\*\*(.+?)\*\*\s*[—–-]\s*([^:\n]+):\s*\*\*([^*]+)\*\*(.*)", block.text, re.S)
    if not match or detect_column_role(match[2])[0] != "code":
        return []
    fields = re.split(r"(?<=[.;])\s+(?=[^:;()\n]{2,80}:)", match[4])
    values = [field.split(":", 1)[1] for field in fields
              if ":" in field and detect_column_role(field.split(":", 1)[0])[0] == "combos"]
    combos = list(dict.fromkeys(combo for value in values for combo in matching_tuples(value, subjects)))
    return [CombinationRecord(clean(match[3]), clean(match[1]), combos, block)] if combos else []
