"""Create a NEW offline review checkpoint from sealed source and an explicit plan.

Never calls ModelOps, writes source DB rows, approves, applies, publishes or indexes.
The plan is agent-authored review DATA, not a human decision or a model response.
"""
import argparse
import asyncio
import copy
import hashlib
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.core.storage import LocalStorageDriver
from app.modules.knowledge.services.qnu_serving import load_document
from app.modules.knowledge.services.semantic_annotations import (
    SemanticAnnotations,
    _digest,
    semantic_input_hash,
    stage_semantic_annotations,
)
from app.modules.knowledge.services.semantic_context import ContextBuilder
from app.modules.knowledge.services.semantic_evidence import (
    source_identity,
    verify_annotation_bindings,
)


def read_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, value) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")


def verify_checkpoint(root: Path) -> dict:
    root = root.resolve()
    manifest = read_json(root / "manifest.json")
    for name, expected in manifest.items():
        path = (root / name).resolve()
        if not path.is_relative_to(root) or hashlib.sha256(path.read_bytes()).hexdigest() != expected:
            raise ValueError("CHECKPOINT_FILE_HASH_MISMATCH")
    checkpoint, proposal, before = (read_json(root / name) for name in ("checkpoint.json", "proposal.json", "before.json"))
    if (proposal["proposal_hash"] != _digest({k: v for k, v in proposal.items() if k != "proposal_hash"})
            or proposal["proposal_hash"] != checkpoint["proposal_hash"]
            or proposal["input_hash"] != checkpoint["input_hash"]
            or proposal["input_hash"] != semantic_input_hash(before)
            or checkpoint["source"] != source_identity(before)):
        raise ValueError("CHECKPOINT_PROPOSAL_OR_SOURCE_MISMATCH")
    verify_annotation_bindings(before, SemanticAnnotations.model_validate(proposal["annotations"]))
    return {"manifest": manifest, "checkpoint": checkpoint, "proposal": proposal, "before": before}


async def prepare(original: Path, plan: dict, output: Path) -> dict:
    original, output = original.resolve(), output.resolve()
    verified = verify_checkpoint(original)
    checkpoint, proposal, artifact = (verified[key] for key in ("checkpoint", "proposal", "before"))
    if plan["original_proposal_hash"] != proposal["proposal_hash"] or output.exists() or output.is_relative_to(original):
        raise ValueError("REVISED_CHECKPOINT_TARGET_OR_PARENT_INVALID")
    annotations = SemanticAnnotations.model_validate(plan["annotations"])
    if any(note.assertion_version != 1 for note in annotations.notes):
        raise ValueError("REVISED_CHECKPOINT_REQUIRES_ASSERTION_SCOPES")
    reference = read_json(original / "source-reference.json")
    snapshot = reference["path"].split("." + reference["sha256"])[0]
    document = await load_document(reference, binding_id=reference["document_id"], revision_id=reference["revision_id"],
        origin_hash=checkpoint["fixture_sha256"], snapshot_path=snapshot, storage=LocalStorageDriver(str(original / "objects")))
    builder = ContextBuilder(artifact, document)
    unit_ids = list(dict.fromkeys([*plan["review_unit_ids"],
        *(uid for issue in proposal["context_review"]["issues"] for uid in issue["unit_ids"])]))
    context = builder.review_context(unit_ids, checkpoint["target_table_ids"])
    if context["heading_without_body"]:
        raise ValueError("REVIEW_HEADING_BODY_MISSING")
    required = {note.note_unit_id for note in annotations.notes}
    required.update(b.source_unit_id for note in annotations.notes for b in note.related_evidence)
    required.update(e["evidence_binding"]["source_unit_id"] for item in plan.get("reference_assessments", []) for e in item["evidence"])
    if not required.issubset({u["id"] for u in context["units"]}):
        raise ValueError("REVISED_ASSERTION_SOURCE_NOT_REVIEWED")
    revised = copy.deepcopy(artifact)
    revised["semantic_annotations"] = copy.deepcopy(proposal)
    review = copy.deepcopy(proposal["context_review"])
    review["reference_assessments"] = plan.get("reference_assessments", [])
    if plan.get("display_labels"):
        review["display_labels"] = plan["display_labels"]
    staged = stage_semantic_annotations(revised, annotations,
        model={"origin": "agent_review_revision", "original_proposal_hash": proposal["proposal_hash"], "new_model_calls": 0},
        context_review=review)
    if staged["proposal_hash"] == proposal["proposal_hash"]:
        raise ValueError("REVISED_CHECKPOINT_HASH_NOT_NEW")
    output.mkdir(parents=True, exist_ok=False)
    write_json(output / "proposal.json", staged)
    write_json(output / "pending-projection.json", revised)
    write_json(output / "review-context.json", context)
    receipt = {"status": "WAITING_FOR_REVIEW", "source": source_identity(artifact), "input_hash": semantic_input_hash(artifact),
        "original_checkpoint": str(original), "original_proposal_hash": proposal["proposal_hash"],
        "original_manifest_sha256": hashlib.sha256((original / "manifest.json").read_bytes()).hexdigest(),
        "proposal_hash": staged["proposal_hash"], "human_approved": False, "source_applied": False,
        "new_model_calls": 0, "origin": "agent_review_revision", "offline_only": True,
        "retained_original_issue_ids": [issue["issue_id"] for issue in proposal["context_review"]["issues"]]}
    write_json(output / "checkpoint.json", receipt)
    verify_checkpoint(original)  # The original sealed files must remain byte-for-byte intact.
    files = {str(path.relative_to(output)): hashlib.sha256(path.read_bytes()).hexdigest() for path in output.iterdir() if path.is_file()}
    write_json(output / "manifest.json", files)
    return receipt


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--original", type=Path, required=True)
    parser.add_argument("--plan", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(asyncio.run(prepare(args.original, read_json(args.plan), args.output)), ensure_ascii=True))
