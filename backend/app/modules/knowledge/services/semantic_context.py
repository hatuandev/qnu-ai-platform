"""Bounded structural views of a verified document; adjacency never proves scope."""

import json
import re
import unicodedata
from collections import defaultdict

from pydantic import BaseModel, ConfigDict, Field

from app.modules.knowledge.services.semantic_evidence import (
    digest,
    evidence_spans,
    source_identity,
    verify_source_document,
)


class SemanticContextPolicy(BaseModel):
    model_config = ConfigDict(extra="forbid")
    max_packet_bytes: int = Field(48000, ge=2000, le=200000)
    max_total_bytes: int = Field(1000000, ge=2000, le=2000000)
    max_packets: int = Field(24, ge=1, le=64)
    max_calls: int = Field(24, ge=1, le=64)
    max_units: int = Field(120, ge=4, le=1000)
    max_expansions: int = Field(2, ge=0, le=4)
    neighbor_units: int = Field(3, ge=0, le=12)
    max_evidence_chars: int = Field(2000, ge=100, le=5000)
    max_output_tokens: int = Field(6000, ge=512, le=8192)
    run_seconds: float = Field(120, gt=0, le=600)
    call_seconds: float = Field(90, gt=0, le=180)


def model_context(packet: dict) -> dict:
    return {key: value for key, value in packet.items() if not key.startswith("_")}


def context_bytes(packet: dict) -> int:
    return len(json.dumps(model_context(packet), ensure_ascii=False).encode())


def packet_usage(packet: dict) -> dict:
    identities = {unit["id"] for unit in packet["units"]}
    for table in packet["tables"]:
        rows = [row["id"] for row in table["rows"]]
        if len(rows) != len(set(rows)) or len(table["visible_row_ids"]) != len(set(table["visible_row_ids"])) or set(rows) != set(table["visible_row_ids"]):
            raise ValueError("CONTEXT_VISIBLE_ROWS_INVALID")
        identities.update([table["id"], *rows])
    return {"units": len(identities), "payload_bytes": context_bytes(packet)}


def enforce_packet_budget(packet: dict, policy: SemanticContextPolicy) -> dict:
    usage = packet_usage(packet)
    if usage["units"] > policy.max_units or usage["payload_bytes"] > policy.max_packet_bytes:
        raise ValueError("CONTEXT_EXPANSION_BUDGET")
    return usage


def fits_packet(packet: dict, policy: SemanticContextPolicy) -> bool:
    usage = packet_usage(packet)
    return usage["units"] <= policy.max_units and usage["payload_bytes"] <= policy.max_packet_bytes


def _label(value: str) -> str:
    # Only reference lookup uses representation normalization; evidence never does.
    return " ".join(unicodedata.normalize("NFC", value).casefold().split()).strip("# .:")


class ContextBuilder:
    def __init__(self, artifact: dict, document, policy: SemanticContextPolicy | None = None):
        from app.modules.knowledge.services.semantic_annotations import semantic_input_hash

        self.artifact, self.document = artifact, document
        self.policy = policy or SemanticContextPolicy()
        self.manifest = verify_source_document(artifact, document)
        self.units = {unit.id: unit for unit in self.manifest.units}
        self.order = {unit.id: index for index, unit in enumerate(self.manifest.units)}
        self.blocks = {block.id: block for block in document.blocks}
        self.tables = {table["id"]: table for table in artifact["tables"]}
        self.trace: list[dict] = []
        self.unexamined: list[str] = []
        self.local_ids: dict[str, list[str]] = {}
        self.deferred: dict[str, list[str]] = {}
        self.input_hash = semantic_input_hash(artifact)
        self._evidence_cache: dict[tuple, list[dict]] = {}
        self.labels: dict[str, list[str]] = defaultdict(list)
        for unit in self.manifest.units:
            block = self.blocks.get(unit.qnu_block_id)
            # Numbered row/footnote labels alone are not document references.
            # Row identifiers remain selectable through the table directory.
            labels = ([block.source_label] if block and block.source_label
                      and unit.kind != "table" and any(char.isalpha() for char in block.source_label) else [])
            if unit.kind == "heading":
                labels.append(unit.text.lstrip("# "))
                # Generic structural label: words + ordinal, without domain keywords.
                prefix = re.match(r"^([^\W\d_]+(?:\s+[^\W\d_]+){0,2}\s+(?:\d+|[IVXLCDM]+))\b", unit.text.lstrip("# "))
                if prefix:
                    labels.append(prefix[1])
            for label in labels:
                if label and unit.id not in self.labels[_label(label)]:
                    self.labels[_label(label)].append(unit.id)

    def _evidence(self, unit_id: str, column_id: str | None = None) -> list[dict]:
        key = unit_id, column_id
        if key not in self._evidence_cache:
            self._evidence_cache[key] = evidence_spans(self.artifact, unit_id, column_id=column_id,
                max_chars=self.policy.max_evidence_chars, input_hash=self.input_hash)
        return self._evidence_cache[key]

    def _related(self, initial: list[str]) -> list[str]:
        included = set(initial)
        frontier = list(initial)
        for depth in range(self.policy.max_expansions + 1):
            following = []
            for unit_id in frontier:
                unit = self.units[unit_id]
                refs = [*unit.context_refs, *[ref for values in unit.field_context_refs.values() for ref in values]]
                block = self.blocks.get(unit.qnu_block_id)
                if block:
                    refs.extend("qnu:" + ref for ref in block.context_refs)
                    if block.parent_id:
                        refs.append("qnu:" + block.parent_id)
                # Containers/headers repeat every cell; ancestor headings are context,
                # not references from the focal prose. Scanning them pulls unrelated
                # tables and whole sections into every packet.
                normalized = _label(unit.text) if unit.kind in {"paragraph", "list"} else ""
                for label, candidates in self.labels.items():
                    if label and re.search(r"(?<!\w)" + re.escape(label) + r"(?!\w)", normalized):
                        if len(candidates) == 1 and candidates[0] != unit_id:
                            refs.extend(candidates)
                            target = self.units[candidates[0]]
                            if target.kind == "heading":
                                refs.extend("qnu:" + child.id for child in self.document.blocks
                                            if child.parent_id == target.qnu_block_id and child.type not in {"table", "table_row"})
                        elif unit_id not in candidates:
                            self.trace.append({"reason": "ambiguous_exact_reference", "from": unit_id, "candidates": candidates})
                for ref in dict.fromkeys(refs):
                    if ref not in self.units:
                        self.trace.append({"reason": "missing_reference", "from": unit_id, "target": ref})
                    elif ref not in included:
                        if depth == self.policy.max_expansions or len(included) >= self.policy.max_units:
                            self.trace.append({"reason": "expansion_budget", "from": unit_id, "target": ref})
                        else:
                            included.add(ref)
                            following.append(ref)
                            self.trace.append({"reason": "explicit_or_unique_structural_reference", "from": unit_id, "target": ref, "depth": depth})
            frontier = following
            if not frontier:
                break
        return sorted(included, key=self.order.get)

    def _local(self, table: dict) -> list[str]:
        parent = self.units[table["id"]]
        prose = [unit for unit in self.manifest.units if not unit.is_container and unit.kind != "table"]
        before = [unit.id for unit in prose if unit.end <= parent.start][-self.policy.neighbor_units:] if self.policy.neighbor_units else []
        next_table = min([unit.start for unit in self.manifest.units if unit.is_container and unit.start > parent.start], default=float("inf"))
        next_heading = min([unit.start for unit in prose if unit.kind == "heading" and unit.start >= parent.end], default=float("inf"))
        after = [unit.id for unit in prose if parent.end <= unit.start < min(next_table, next_heading)]
        headings = [unit.id for unit in prose if unit.kind == "heading" and unit.start < parent.start
                    and unit.text.lstrip("# ") in parent.heading_path]
        initial = list(dict.fromkeys([*headings, *before, *after, parent.id + ":header"]))
        self.local_ids[table["id"]] = initial
        return self._related(initial)

    def _packet(self, tables: list[tuple[dict, list[str]]], unit_ids: list[str], *, round_no: int = 0) -> dict:
        evidence, registry = [], {}
        unit_ids = sorted(set(unit_ids), key=self.order.get)
        views = []
        for table, rows in tables:
            fields = dict(zip(table["row_unit_ids"], table["row_fields"], strict=True))
            views.append({"id": table["id"], "columns": table["columns"], "row_count": len(table["row_unit_ids"]),
                "visible_row_ids": rows, "heading_path": self.units[table["id"]].heading_path,
                # Whole-table identity directory allows a group note to span row
                # windows. Cell interpretation still requires full visible fields.
                "row_directory": [{"id": rid, "identifiers": [field["raw"] for field in fields[rid]
                    if re.fullmatch(r"[^\W\d_]+(?:[-_.][^\W_]+)+", field["raw"])]}
                    for rid in table["row_unit_ids"]],
                "rows": [{"id": rid, "fields": [{key: field.get(key) for key in ("column_id", "raw", "state")}
                                                 for field in fields[rid]]} for rid in rows]})
            for row_id in rows:
                for field in fields[row_id]:
                    if field["state"] != "present" or not re.fullmatch(r"[+-]?\d+(?:[.,]\d+)?%?", field["raw"].strip()):
                        evidence.extend(self._evidence(row_id, field["column_id"]))
        units = []
        for unit_id in unit_ids:
            unit = self.units[unit_id]
            block = self.blocks.get(unit.qnu_block_id)
            if unit.is_container or (unit.kind == "table" and not unit.id.endswith(":header")):
                continue
            units.append({"id": unit.id, "kind": block.type if block else unit.kind,
                "parent_id": "qnu:" + block.parent_id if block and block.parent_id else unit.parent_id,
                "text": unit.text, "heading_path": unit.heading_path, "logical_order": self.order[unit.id],
                "page": unit.page_number, "source_locations": unit.source_locations, "context_refs": unit.context_refs})
            if (unit.kind in {"paragraph", "list"} and block and block.type in {"text", "note", "list"}
                    and not unit.text.lstrip().startswith(("```", "~~~"))):
                evidence.extend(self._evidence(unit.id))
        public = []
        for item in evidence:
            registry[item["id"]] = item["binding"]
            public.append({key: value for key, value in item.items() if key != "binding"})
        packet = {"source": source_identity(self.artifact), "tables": views, "units": units, "evidence": public,
            "prior_context_issues": [{key: item[key] for key in ("issue_id", "kind", "unit_ids", "target", "reason")}
                for item in ((self.artifact.get("semantic_annotations") or {}).get("context_review") or {}).get("issues", [])],
            "deferred_related_unit_ids": sorted({uid for table, _ in tables for uid in self.deferred.get(table["id"], [])
                                                 if uid not in unit_ids}, key=self.order.get),
            "coordinate_rule": "half-open Unicode code points in the supplied unit text or raw cell; select evidence IDs, never rewrite quotes",
            "available_related_units": [{"id": unit_id, "labels": [label for label, ids in self.labels.items() if unit_id in ids]}
                                        for unit_id in self.units if self.units[unit_id].kind == "heading"
                                        or any(unit_id in ids for ids in self.labels.values())],
            "round": round_no, "_bindings": registry, "_unit_ids": unit_ids,
            "_tables": [(table["id"], rows) for table, rows in tables]}
        packet["context_id"] = "ctx:" + digest(model_context(packet))[:32]
        return packet

    def packets(self, target_table_ids: list[str] | None = None) -> list[dict]:
        targets = list(self.tables) if target_table_ids is None else target_table_ids
        if len(targets) != len(set(targets)) or not set(targets).issubset(self.tables):
            raise ValueError("CONTEXT_TARGET_INVALID")
        result, examined = [], set()
        def append(table: dict, rows: list[str], local: list[str]):
            if len(result) >= self.policy.max_packets:
                self.unexamined.extend([*local, *rows])
                self.trace.append({"reason": "packet_count_budget", "table_id": table["id"]})
                return
            packet = self._packet([(table, rows)], local)
            if not fits_packet(packet, self.policy):
                if len(rows) > 1:
                    middle = len(rows) // 2
                    append(table, rows[:middle], local); append(table, rows[middle:], local)
                    return
                self.trace.append({"reason": "packet_budget", "table_id": table["id"], "row_ids": rows})
                self.unexamined.extend([*local, *rows])
                return
            result.append(packet)
            examined.update([*local, *rows])
        for table_id in targets:
            table = self.tables[table_id]
            local = self._local(table)
            # Prioritize complete local objects over eagerly expanded remote
            # sections. Deferred IDs stay explicit and can be requested; their
            # prose is still covered by the document's separate packets.
            removable = [uid for uid in local if uid not in self.local_ids[table_id]]
            while removable and context_bytes(self._packet([(table, table["row_unit_ids"])], local)) > self.policy.max_packet_bytes:
                uid = max(removable, key=lambda item: len(self.units[item].text))
                removable.remove(uid)
                local.remove(uid)
                self.deferred.setdefault(table_id, []).append(uid)
                self.trace.append({"reason": "deferred_related_budget", "table_id": table_id, "target": uid})
            append(table, table["row_unit_ids"], local)
        # Prose outside table neighborhoods is not silently discarded.
        if target_table_ids is None:
            remaining = [unit.id for unit in self.manifest.units if not unit.is_container
                         and unit.kind in {"paragraph", "list"} and unit.id not in examined]
            group = []
            for unit_id in remaining:
                # Prose packets carry focal units, not recursively expanded copies
                # of every section they reference. The reference directory and
                # on-demand expansion remain available in each packet.
                trial = self._packet([], [*group, unit_id])
                if group and not fits_packet(trial, self.policy):
                    result.append(self._packet([], group))
                    group = []
                group.append(unit_id)
            if group:
                result.append(self._packet([], group))
        accepted = []
        for packet in result:
            if len(accepted) >= self.policy.max_packets or not fits_packet(packet, self.policy):
                self.unexamined.extend([*packet["_unit_ids"], *(rid for _, rows in packet["_tables"] for rid in rows)])
                self.trace.append({"reason": "packet_count_or_bytes_budget"})
            else:
                accepted.append(packet)
        return accepted

    def expand(self, packet: dict, requested: list[str]) -> dict:
        if (packet["round"] >= self.policy.max_expansions or len(requested) != len(set(requested))
                or not set(requested).issubset(self.units)):
            raise ValueError("CONTEXT_EXPANSION_INVALID_OR_EXHAUSTED")
        children = ["qnu:" + child.id for unit_id in requested if self.units[unit_id].kind == "heading"
                    for child in self.document.blocks if child.parent_id == self.units[unit_id].qnu_block_id]
        ids = sorted(set(packet["_unit_ids"]) | set(self._related([*requested, *children])), key=self.order.get)
        tables = [(self.tables[tid], rows) for tid, rows in packet["_tables"]]
        for unit_id in requested:
            table_id = unit_id if unit_id in self.tables else self.units[unit_id].parent_id
            if table_id in self.tables:
                table = self.tables[table_id]
                additions = table["row_unit_ids"] if unit_id == table_id else [unit_id] if unit_id in table["row_unit_ids"] else []
                previous = next((rows for current, rows in tables if current["id"] == table_id), [])
                rows = [rid for rid in table["row_unit_ids"] if rid in set(previous) | set(additions)]
                tables = [(current, values) for current, values in tables if current["id"] != table_id]
                tables.append((table, rows))
        revised = self._packet(tables, ids, round_no=packet["round"] + 1)
        enforce_packet_budget(revised, self.policy)
        if set(ids) == set(packet["_unit_ids"]) and revised["_tables"] == packet["_tables"]:
            raise ValueError("CONTEXT_EXPANSION_NO_NEW_UNITS")
        self.trace.append({"reason": "model_requested_expansion", "units": requested})
        return revised
