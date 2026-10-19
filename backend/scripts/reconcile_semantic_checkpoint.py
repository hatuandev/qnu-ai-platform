"""Prepare a NEW offline proposal from exact canonical lineage. Never stage or approve."""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.modules.knowledge.normalization.qnu_markdown import (
    QnuStructuredDocument,
    parse_qnu_markdown,
    render_qnu_markdown,
    validate_qnu_markdown,
)
from app.modules.knowledge.services.semantic_annotations import (
    SemanticAnnotations,
    _digest,
    semantic_input_hash,
    stage_semantic_annotations,
)
from app.modules.knowledge.services.semantic_assertions import assertion_identity
from app.modules.knowledge.services.semantic_context_review import (
    make_issue,
    validate_reference_assessments,
)
from app.modules.knowledge.services.semantic_evidence import (
    EvidenceBinding,
    make_binding,
    source_identity,
    source_text,
    verify_binding,
    verify_source_document,
)


def _locations(block) -> tuple:
    return tuple(location.locator for location in block.source_locations if location.locator)


def _ancestors(block, blocks) -> tuple:
    found, seen = [], set()
    while block.parent_id:
        if block.parent_id in seen or block.parent_id not in blocks:
            raise ValueError("RECONCILIATION_PARENT_INVALID")
        seen.add(block.parent_id)
        block = blocks[block.parent_id]
        found.append((block.type, block.body, _locations(block)))
    return tuple(found)


def _columns(table) -> list:
    return [
        {k: v for k, v in column.items() if k != "id"}
        for column in table.attributes.get("columns", [])
    ]


def _row_signature(block, blocks) -> list:
    parent = blocks.get(block.parent_id)
    if parent is None or parent.type != "table":
        raise ValueError("RECONCILIATION_ROW_PARENT_INVALID")
    fields = block.attributes.get("fields") or {}
    columns = parent.attributes.get("columns") or []
    if not columns or set(fields) != {column["id"] for column in columns}:
        raise ValueError("RECONCILIATION_ROW_FIELDS_INVALID")
    return [
        (fields[column["id"]].get("raw"), fields[column["id"]].get("state")) for column in columns
    ]


class ExactSourceMap:
    def __init__(self, old_doc, new_doc, old, new):
        if not old_doc.source.sha256 or old_doc.source.sha256 != new_doc.source.sha256:
            raise ValueError("RECONCILIATION_DOCX_LINEAGE_MISMATCH")
        self.old, self.new = old, new
        self.old_units = {u.id: u for u in verify_source_document(old, old_doc).units}
        self.new_units = {u.id: u for u in verify_source_document(new, new_doc).units}
        self.old_blocks, self.new_blocks = ({b.id: b for b in d.blocks} for d in [old_doc, new_doc])
        if len(self.old_blocks) != len(old_doc.blocks) or len(self.new_blocks) != len(
            new_doc.blocks
        ):
            raise ValueError("RECONCILIATION_DUPLICATE_BLOCK_ID")
        self.mapping = {}

    def unit(self, uid: str) -> str:
        if uid in self.mapping:
            return self.mapping[uid]
        original = self.old_units.get(uid)
        block = self.old_blocks.get(original.qnu_block_id) if original else None
        if block is None or not _locations(block):
            raise ValueError("RECONCILIATION_SOURCE_LOCATOR_MISSING")
        candidates = [
            b
            for b in self.new_blocks.values()
            if b.type == block.type
            and _locations(b) == _locations(block)
            and _ancestors(b, self.new_blocks) == _ancestors(block, self.old_blocks)
        ]
        if block.type == "table_row":
            candidates = [
                b
                for b in candidates
                if _row_signature(block, self.old_blocks) == _row_signature(b, self.new_blocks)
            ]
        else:
            candidates = [b for b in candidates if b.body == block.body]
        if block.type == "table":

            def grid(artifact, bid):
                tables = [t for t in artifact["tables"] if t["id"] == "qnu:" + bid]
                if len(tables) != 1:
                    return None
                table = tables[0]
                return (
                    len(table["columns"]),
                    [[(f["raw"], f["state"]) for f in row] for row in table["row_fields"]],
                )

            original_grid = grid(self.old, block.id)
            candidates = [
                b
                for b in candidates
                if original_grid is not None and grid(self.new, b.id) == original_grid
            ]
        units = [
            u
            for u in self.new_units.values()
            if any(b.id == u.qnu_block_id for b in candidates)
            and u.kind == original.kind
            and u.is_container == original.is_container
        ]
        if len(units) != 1:
            raise ValueError("RECONCILIATION_UNIQUE_STRUCTURAL_SOURCE_REQUIRED")
        self.mapping[uid] = units[0].id
        return units[0].id

    def column(self, table_id: str, column_id: str) -> str:
        old_table = self.old_blocks[self.old_units[table_id].qnu_block_id]
        new_table = self.new_blocks[self.new_units[self.unit(table_id)].qnu_block_id]
        ids = [c["id"] for c in old_table.attributes["columns"]]
        if ids.count(column_id) != 1:
            raise ValueError("RECONCILIATION_COLUMN_ROLE_MISMATCH")
        index = ids.index(column_id)
        if _columns(old_table)[index] != _columns(new_table)[index]:
            raise ValueError("RECONCILIATION_COLUMN_ROLE_MISMATCH")
        return new_table.attributes["columns"][index]["id"]

    def binding(self, raw: dict) -> dict:
        old = EvidenceBinding.model_validate(raw)
        old_text = source_text(self.old, old.source_unit_id, old.column_id)
        verify_binding(self.old, old, old_text[old.start : old.end], old.source_unit_id)
        if old.column_id is not None:
            raise ValueError("RECONCILIATION_PROSE_ONLY")
        uid = self.unit(old.source_unit_id)
        if source_text(self.new, uid) != old_text:
            raise ValueError("RECONCILIATION_FULL_SOURCE_TEXT_CHANGED")
        return make_binding(self.new, uid, old.start, old.end).model_dump()

    def bindings(self, value):
        if isinstance(value, list):
            return [self.bindings(item) for item in value]
        if isinstance(value, dict):
            if "coordinate_space" in value and "evidence_id" in value:
                return self.binding(value)
            return {key: self.bindings(item) for key, item in value.items()}
        return value


def reconcile_proposal(old_doc, new_doc, old: dict, new: dict, proposal: dict) -> dict:
    """No matching by IDs alone, normalized text, filename, fuzzy score or embeddings."""
    if (
        proposal.get("status") not in {"proposed", "empty"}
        or "review" in proposal
        or proposal.get("proposal_hash")
        != _digest({k: v for k, v in proposal.items() if k != "proposal_hash"})
        or proposal.get("input_hash") != semantic_input_hash(old)
    ):
        raise ValueError("RECONCILIATION_PENDING_ENVELOPE_INVALID")
    annotations = SemanticAnnotations.model_validate(proposal["annotations"])
    if (
        annotations.cells
        or annotations.limitations
        or any(n.assertion_version != 1 for n in annotations.notes)
    ):
        raise ValueError("RECONCILIATION_REQUIRES_BOUND_ASSERTIONS")
    mapper = ExactSourceMap(old_doc, new_doc, old, new)
    validate_reference_assessments(old, proposal.get("context_review"), annotations.notes)
    mapped, results, assertion_ids = [], [], {}
    labels = (proposal.get("context_review") or {}).get("display_labels") or {}
    for index, note in enumerate(annotations.notes, 1):
        label = labels.get("assertions", {}).get(assertion_identity(note), f"A{index:02}")
        try:
            raw = mapper.bindings(note.model_dump())
            raw.update(
                note_unit_id=mapper.unit(note.note_unit_id),
                table_id=mapper.unit(note.table_id),
                row_unit_ids=[mapper.unit(uid) for uid in note.row_unit_ids],
                column_ids=[mapper.column(note.table_id, cid) for cid in note.column_ids],
            )
            current = type(note).model_validate(raw)
            assertion_ids[assertion_identity(note)] = assertion_identity(current)
            mapped.append(current)
            results.append(
                {
                    "label": label,
                    "status": "MAPPED",
                    "before": note.model_dump(),
                    "after": current.model_dump(),
                }
            )
        except ValueError as exc:
            results.append(
                {
                    "label": label,
                    "status": "BLOCKED",
                    "reason": str(exc),
                    "before": note.model_dump(),
                }
            )
    reference_results = []
    for item in (proposal.get("context_review") or {}).get("reference_assessments", []):
        try:
            mapper.bindings(item)
            if not set(item["assertion_ids"]).issubset(assertion_ids):
                raise ValueError("RECONCILIATION_REFERENCE_TARGET_BLOCKED")
            reference_results.append({"issue_id": item["issue_id"], "status": "MAPPED"})
        except ValueError as exc:
            reference_results.append(
                {"issue_id": item["issue_id"], "status": "BLOCKED", "reason": str(exc)}
            )
    result = {
        "status": "RECONCILIATION_BLOCKED",
        "old_proposal_hash": proposal["proposal_hash"],
        "canonical_source": source_identity(new),
        "assertions": results,
        "references": reference_results,
        "source_unit_mapping": mapper.mapping,
        "proposal": None,
        "staged_in_application": False,
        "human_approved": False,
    }
    if any(r["status"] == "BLOCKED" for r in [*results, *reference_results]):
        return result
    review = copy.deepcopy(proposal.get("context_review") or {})
    issues, issue_ids = [], {}
    for item in review.get("issues", []):
        if (
            make_issue(old, item["kind"], item["unit_ids"], item["target"], item["reason"])[
                "issue_id"
            ]
            != item["issue_id"]
        ):
            raise ValueError("RECONCILIATION_ISSUE_ID_INVALID")
        target = copy.deepcopy(item["target"])
        table = target.get("table_id")
        if table:
            target["table_id"] = mapper.unit(table)
            target["column_ids"] = [
                mapper.column(table, cid) for cid in target.get("column_ids", [])
            ]
        for key in ["row_unit_ids", "table_ids"]:
            if key in target:
                target[key] = [mapper.unit(uid) for uid in target[key]]
        if "assertion_id" in target:
            target["assertion_id"] = assertion_ids[target["assertion_id"]]
        issue = make_issue(
            new,
            item["kind"],
            [mapper.unit(uid) for uid in item["unit_ids"]],
            target,
            item["reason"],
        )
        issues.append(issue)
        issue_ids[item["issue_id"]] = issue["issue_id"]
    review["issues"] = issues
    review.pop("reconciliation", None)
    review.pop("reprocessed_issues", None)
    for item in review.get("unresolved", []):
        item["unit_ids"] = [mapper.unit(uid) for uid in item["unit_ids"]]
    review["reference_assessments"] = mapper.bindings(review.get("reference_assessments", []))
    for item in review["reference_assessments"]:
        item["issue_id"] = issue_ids[item["issue_id"]]
        item["assertion_ids"] = [assertion_ids[uid] for uid in item["assertion_ids"]]
        for link in item.get("links", []):
            link["assertion_id"] = assertion_ids[link["assertion_id"]]
    if "target_table_ids" in review:
        review["target_table_ids"] = [mapper.unit(uid) for uid in review["target_table_ids"]]
    review["display_labels"] = {
        "assertions": {assertion_ids[k]: v for k, v in labels.get("assertions", {}).items()},
        "issues": {issue_ids[k]: v for k, v in labels.get("issues", {}).items()},
    }
    staged = copy.deepcopy(new)
    pending = stage_semantic_annotations(
        staged,
        SemanticAnnotations(notes=mapped),
        context_review=review,
        model={
            "origin": "canonical_source_reconciliation",
            "old_proposal_hash": proposal["proposal_hash"],
            "new_model_calls": 0,
        },
    )
    result.update(status="PREPARED_NOT_STAGED", proposal=pending, issue_id_mapping=issue_ids)
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--original", type=Path, required=True)
    parser.add_argument("--revised", type=Path, required=True)
    parser.add_argument("--canonical", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if any(
        args.output.resolve().is_relative_to(root.resolve())
        for root in [args.original, args.revised, args.canonical]
    ):
        raise ValueError("RECONCILIATION_OUTPUT_MUST_NOT_CHANGE_INPUT_CHECKPOINT")
    read = lambda p: json.loads(p.read_text(encoding="utf-8"))

    def sealed(root):
        for name, checksum in read(root / "manifest.json").items():
            path = (root / name).resolve()
            if (
                not path.is_relative_to(root.resolve())
                or hashlib.sha256(path.read_bytes()).hexdigest() != checksum
            ):
                raise ValueError("RECONCILIATION_CHECKPOINT_CHECKSUM")

    sealed(args.original)
    sealed(args.revised)
    if args.output.exists():
        raise ValueError("RECONCILIATION_OUTPUT_EXISTS")
    ref = read(args.original / "source-reference.json")
    old_path = (args.original / "objects" / ref["structured_path"]).resolve()
    if not old_path.is_relative_to((args.original / "objects").resolve()):
        raise ValueError("RECONCILIATION_SOURCE_PATH_INVALID")
    old_bytes = old_path.read_bytes()
    if hashlib.sha256(old_bytes).hexdigest() != ref["structured_sha256"]:
        raise ValueError("RECONCILIATION_SOURCE_CHECKSUM")
    old_doc = QnuStructuredDocument.model_validate_json(old_bytes)
    new_doc = QnuStructuredDocument.model_validate_json(
        (args.canonical / "structured.json").read_bytes()
    )
    revision = read(args.canonical / "revision.json")
    reference = revision["reference"]
    for name, key in [
        ("standard.md", "sha256"),
        ("structured.json", "structured_sha256"),
        ("source.docx", None),
    ]:
        expected = reference[key] if key else old_doc.source.sha256
        if hashlib.sha256((args.canonical / name).read_bytes()).hexdigest() != expected:
            raise ValueError("RECONCILIATION_CANONICAL_CHECKSUM")
    expected_md = render_qnu_markdown(
        new_doc, document_id=revision["binding_id"], revision_id=revision["revision_id"]
    )
    actual_md = (args.canonical / "standard.md").read_bytes().decode("utf-8")
    parsed, expected = parse_qnu_markdown(actual_md), parse_qnu_markdown(expected_md)
    # Match the existing pair loader's parity contract. Stored bytes above still
    # require their exact checksums; YAML object-key order confers no new identity.
    if (
        not validate_qnu_markdown(actual_md).ok
        or parsed.frontmatter != expected.frontmatter
        or [(b.metadata, b.body) for b in parsed.blocks]
        != [(b.metadata, b.body) for b in expected.blocks]
    ):
        raise ValueError("RECONCILIATION_CANONICAL_PAIR_PARITY")
    old = read(args.original / "before.json")
    new = read(args.canonical / "base-projection.json")
    if source_identity(new) != {
        k: reference[k] for k in ["document_id", "revision_id", "sha256", "structured_sha256"]
    }:
        raise ValueError("RECONCILIATION_CANONICAL_IDENTITY")
    result = reconcile_proposal(old_doc, new_doc, old, new, read(args.revised / "proposal.json"))
    args.output.mkdir(parents=True, exist_ok=False)

    def write(name, data):
        (args.output / name).write_text(
            json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n"
        )

    write("reconciliation.json", result)
    if result["proposal"]:
        write(
            "import-package.json",
            {
                "contract": "qnu-semantic-checkpoint-v1",
                "source_artifact": new,
                "proposal": result["proposal"],
            },
        )
    write(
        "manifest.json",
        {
            p.name: hashlib.sha256(p.read_bytes()).hexdigest()
            for p in args.output.iterdir()
            if p.is_file()
        },
    )
    sealed(args.original)
    sealed(args.revised)
    print(
        json.dumps(
            {
                "status": result["status"],
                "mapped": sum(r["status"] == "MAPPED" for r in result["assertions"]),
                "blocked": sum(r["status"] == "BLOCKED" for r in result["assertions"]),
                "staged": False,
            }
        )
    )


if __name__ == "__main__":
    main()
