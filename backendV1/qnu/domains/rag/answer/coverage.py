"""Expose missing answer requirements without retries or claims of semantic proof."""

from typing import TYPE_CHECKING, Literal

from pydantic import BaseModel, ConfigDict, Field

from qnu.platform.errors import AppException

if TYPE_CHECKING:
    from qnu.domains.rag.answer.schemas import EvidenceSource, ModelAnswer

VERSION = "qnu.rag.coverage/v2"


class Requirement(BaseModel):
    model_config = ConfigDict(extra="forbid")
    label: str = Field(min_length=1, max_length=500)
    status: Literal["covered", "missing", "conflicting"]
    evidence_ids: list[str] = Field(max_length=20)


class StructuralCoverage(BaseModel):
    label: str
    required_units: int
    provided_units: int
    cited_units: int
    status: Literal["covered", "partial"]
    uncovered_evidence_ids: list[str] = Field(default_factory=list)


class CoverageReport(BaseModel):
    status: Literal["complete", "partial", "insufficient", "not_assessed"]
    requirements: list[Requirement] = Field(default_factory=list)
    structures: list[StructuralCoverage] = Field(default_factory=list)
    basis: str = "model_requirements_and_source_citations"
    scope_status: Literal["bounded", "unresolved", "not_requested"] = "not_requested"


def plan_for(sources: list["EvidenceSource"], context: dict) -> dict:
    ids = {s.chunk_id: s.evidence_id for s in sources}
    return {
        "version": VERSION,
        "scope": "retrieved_published_sources_only",
        "unresolved_references": context.get("structure", {}).get("unresolved_references", []),
        "groups": [
            {
                "label": g["label"],
                "kind": g["kind"],
                "units": [
                    {
                        "evidence_ids": list(
                            dict.fromkeys(ids[c] for c in u["chunk_ids"] if c in ids)
                        )
                    }
                    for u in g["units"]
                ],
                "unprovided_units": sum(
                    not any(c in ids for c in u["chunk_ids"]) for u in g["units"]
                ),
            }
            for g in context.get("structure", {}).get("groups", [])
        ],
    }


def referenced_ids(answer: "ModelAnswer", coverage: CoverageReport) -> set[str]:
    """Keep every public coverage witness in the revalidated response snapshot."""
    return (
        {eid for statement in answer.statements for eid in statement.evidence_ids}
        | {eid for item in coverage.requirements for eid in item.evidence_ids}
        | {eid for group in coverage.structures for eid in group.uncovered_evidence_ids}
    )


def _requirements(answer: "ModelAnswer", sources: list["EvidenceSource"]) -> list[Requirement]:
    allowed = {s.evidence_id for s in sources}
    used = {eid for statement in answer.statements for eid in statement.evidence_ids}
    requirements = []
    for item in answer.assessment:
        if (
            len(set(item.evidence_ids)) != len(item.evidence_ids)
            or not set(item.evidence_ids) <= allowed
        ):
            raise AppException(
                "Căn cứ đánh giá phạm vi không hợp lệ.",
                code="answer_coverage_invalid",
                status_code=502,
            )
        if item.status == "covered" and (
            not item.evidence_ids or not set(item.evidence_ids) <= used
        ):
            item = item.model_copy(update={"status": "missing"})
        requirements.append(item)
    return requirements


def _structures(
    answer: "ModelAnswer", sources: list["EvidenceSource"], context: dict
) -> list[StructuralCoverage]:
    used = {eid for statement in answer.statements for eid in statement.evidence_ids}
    structures = []
    by_chunk = {s.chunk_id: s.evidence_id for s in sources}
    for group in context.get("structure", {}).get("groups", []):
        units = [{by_chunk[c] for c in u["chunk_ids"] if c in by_chunk} for u in group["units"]]
        if group["kind"] == "continuation" and not any(unit & used for unit in units):
            # Completing a retrieved sentence does not make it a question requirement.
            continue
        supplied = sum(bool(unit) for unit in units)
        cited = sum(bool(unit & used) for unit in units)
        structures.append(
            StructuralCoverage(
                label=group["label"],
                required_units=len(units),
                provided_units=supplied,
                cited_units=cited,
                status="covered" if cited == len(units) else "partial",
                uncovered_evidence_ids=sorted(
                    {eid for unit in units if not unit & used for eid in unit}
                ),
            )
        )
    return structures


def _scope_status(context: dict, structures: list[StructuralCoverage]) -> str:
    return (
        "unresolved"
        if context.get("structure", {}).get("unresolved_references")
        else "bounded"
        if any(
            g.get("units") and g["kind"] != "continuation"
            for g in context.get("structure", {}).get("groups", [])
        )
        else "unresolved"
        if context.get("structure", {}).get("enumeration_requested", False)
        else "not_requested"
    )


def assess(answer: "ModelAnswer", sources: list["EvidenceSource"], context: dict) -> CoverageReport:
    """Structural citation coverage complements, but never replaces, entailment checks."""
    requirements = _requirements(answer, sources)
    structures = _structures(answer, sources, context)
    scope_status = _scope_status(context, structures)
    partial = (
        scope_status == "unresolved"
        or any(r.status != "covered" for r in requirements)
        or any(s.status != "covered" for s in structures)
    )
    status = (
        "insufficient"
        if answer.status == "insufficient_evidence"
        else "partial"
        if partial
        else "complete"
        if requirements
        else "not_assessed"
    )
    return CoverageReport(
        status=status, requirements=requirements, structures=structures, scope_status=scope_status
    )
