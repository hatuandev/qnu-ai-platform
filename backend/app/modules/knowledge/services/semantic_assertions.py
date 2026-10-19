"""Exact canonical spans with independent targets; legacy source-unit links stay intact."""
from app.modules.knowledge.normalization.retrieval_models import (
    SourceUnit,
    TemporalScope,
    UnitManifest,
)
from app.modules.knowledge.services.semantic_evidence import digest, source_text, verify_binding


def assertion_identity(note) -> str:
    return "assertion:" + digest({key: value for key, value in note.model_dump().items()
        if key not in {"reason", "evidence_quote"}})


def _unit(manifest: UnitManifest, binding, scope: dict, role: str) -> SourceUnit:
    source = next(u for u in manifest.units if u.id == binding.source_unit_id)
    if source.kind not in {"paragraph", "list"} or source.text.lstrip().startswith(("```", "~~~")):
        raise ValueError("ASSERTION_REFERENCE_REQUIRES_SOURCE_PROSE")
    metadata = {**scope, "role": role, "binding": binding.model_dump()}
    uid = "qnu:assertion:" + digest(metadata)
    return source.model_copy(update={"id": uid, "kind": "paragraph",
        "text": source.text[binding.start:binding.end],
        "start": source.start + binding.start, "end": source.start + binding.end,
        "temporal": TemporalScope(),
        "context_refs": [], "field_context_refs": {}, "field_usage": {}, "semantic_scope": metadata})


def attach_assertion(artifact: dict, manifest: UnitManifest, note) -> str:
    if note.evidence_binding is None or note.evidence_binding.column_id is not None:
        raise ValueError("ASSERTION_REQUIRES_PROSE_BINDING")
    scope = {"version": 1, "assertion_id": assertion_identity(note), "table_id": note.table_id,
        "scope": note.scope, "row_unit_ids": note.row_unit_ids, "column_ids": note.column_ids}
    if note.context_kind == "workflow":
        scope.update(context_kind="workflow", context_label=note.context_label)
    units = []
    for binding in [note.evidence_binding, *note.related_evidence]:
        quote = source_text(artifact, binding.source_unit_id)[binding.start:binding.end]
        verify_binding(artifact, binding, quote, binding.source_unit_id)
        if binding.column_id is not None:
            raise ValueError("ASSERTION_REFERENCE_REQUIRES_PROSE")
        units.append(_unit(manifest, binding, scope, "assertion" if not units else "reference"))
    root = units[0]
    root.context_refs = list(dict.fromkeys(unit.id for unit in units[1:] if unit.id != root.id))
    by_id = {unit.id: unit for unit in manifest.units}
    for unit in units:
        if unit.id in by_id:
            raise ValueError("Duplicate assertion source span")
        manifest.units.append(unit)
        by_id[unit.id] = unit
    manifest.units.sort(key=lambda unit: (unit.start, unit.end, unit.id))
    return root.id


def validate_assertion_unit(unit: SourceUnit, by_id: dict[str, SourceUnit]) -> None:
    from app.modules.knowledge.services.semantic_evidence import EvidenceBinding
    metadata = unit.semantic_scope
    binding = EvidenceBinding.model_validate(metadata["binding"])
    source = by_id.get(binding.source_unit_id)
    if (source is None or source.semantic_scope or source.is_container or binding.column_id is not None
            or unit.id != "qnu:assertion:" + digest(metadata)
            or unit.text != source.text[binding.start:binding.end]
            or (unit.start, unit.end) != (source.start + binding.start, source.start + binding.end)):
        raise ValueError("ASSERTION_CANONICAL_SPAN_MISMATCH")


def assertion_issues(artifact: dict, notes: list, existing: list | None = None) -> list[dict]:
    from app.modules.knowledge.services.semantic_context_review import make_issue
    def covered(note) -> bool:
        binding = note.evidence_binding
        target = {"table_id": note.table_id, "row_unit_ids": note.row_unit_ids, "column_ids": note.column_ids}
        return bool(binding and binding.start == 0 and binding.end == len(source_text(artifact, note.note_unit_id))
            and any(issue["kind"] == "scope_confirmation_required" and issue["unit_ids"] == [note.note_unit_id]
                    and issue["target"] == target for issue in existing or []))
    return [make_issue(artifact, "scope_confirmation_required", [note.note_unit_id],
        {"table_id": note.table_id, "row_unit_ids": note.row_unit_ids, "column_ids": note.column_ids,
         "assertion_id": assertion_identity(note)},
        "Đối chiếu assertion, toàn đơn vị nguồn, tập đích và các điều kiện loại trừ.")
        for note in notes if note.assertion_version == 1 and not covered(note)]
