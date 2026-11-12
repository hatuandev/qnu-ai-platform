"""Deterministic, source-verified registration information; never a publication decision."""

from collections import defaultdict

from pydantic import ValidationError

from qnu.domains.knowledge.compilation.supplement import RULE_VERSION, automatic_entries
from qnu.domains.knowledge.metadata import RetrievalAnnotation, validate_annotations
from qnu.domains.knowledge.publication.evidence import VersionBundle, digest
from qnu.platform.errors import AppException


def preview(bundle: VersionBundle) -> dict:
    # Keep competing local years/programs local. Only independently corroborated
    # document-wide fields can apply globally; contradictions remain unknown.
    fields = defaultdict(dict)
    for entry in automatic_entries(bundle.content, bundle.documents):
        item = entry["annotation"]
        values = item["values"]
        for field, value in {**values, **values.get("attributes", {})}.items():
            if field == "attributes":
                continue
            key = (item["target"], field, field not in values)
            fields[key].setdefault(digest(value), {"value": value, "evidence": item["evidence"]})
    grouped = {}
    for (target, field, custom), choices in sorted(fields.items()):
        if len(choices) != 1:
            continue
        selected = next(iter(choices.values()))
        if target == "document" and any(
            (
                other != "document"
                and name == field
                and attr == custom
                and set(other_choices) != set(choices)
            )
            for (other, name, attr), other_choices in fields.items()
        ):
            continue
        item = grouped.setdefault(target, {"target": target, "values": {}, "evidence": []})
        dest = item["values"].setdefault("attributes", {}) if custom else item["values"]
        dest[field] = selected["value"]
        item["evidence"].extend(e for e in selected["evidence"] if e not in item["evidence"])
    annotations = []
    for item in grouped.values():
        try:
            item = RetrievalAnnotation.model_validate(item).model_dump(
                mode="json", exclude_none=True
            )
            validate_annotations([item], bundle.content, bundle.documents, strict_roles=True)
        except (ValidationError, AppException):
            # Do not block registration or turn uncertain extracted values into facts.
            continue
        annotations.append(item)
    validate_annotations(annotations, bundle.content, bundle.documents, strict_roles=True)
    return {
        "rules_version": RULE_VERSION,
        "annotations": annotations,
        "sha256": digest(
            {
                "bundle_sha256": bundle.bundle_sha256,
                "rules_version": RULE_VERSION,
                "annotations": annotations,
            }
        ),
    }
