"""Deterministic, source-verified registration information; never a publication decision."""

import re
from collections import defaultdict

from pydantic import ValidationError

from qnu.domains.knowledge.compilation.supplement import RULE_VERSION, automatic_entries
from qnu.domains.knowledge.metadata import RetrievalAnnotation, validate_annotations
from qnu.domains.knowledge.publication.evidence import VersionBundle, digest
from qnu.platform.errors import AppException

EXTENSION = re.compile(r"^gia\s+hạn\b", re.IGNORECASE)


def _confirmed_extension(events: list[dict]) -> bool:
    if len(events) != 2 or events[0]["kind"] != "registration_deadline":
        return False
    if any(not (event.get("moment") or {}).get("date") for event in events):
        return False
    earlier, later = sorted(events, key=lambda event: event["moment"]["date"])
    return bool(
        not EXTENSION.match(earlier["label"])
        and EXTENSION.match(later["label"])
        and earlier["moment"]["date"] < later["moment"]["date"]
    )


def _event_time(event: dict) -> str:
    times = {key: event.get(key) for key in ("moment", "window_start", "relative")}
    for key in ("dates", "end_exclusive"):
        if event.get(key) is not None:
            times[key] = event[key]
    return digest(times)


def _event_scope(event: dict) -> tuple:
    moment = event.get("window_start") or event.get("moment") or {}
    days = event.get("dates") or []
    year = (moment.get("date") or "")[:4] or str(moment.get("year") or "")
    if days:
        year = ",".join(sorted({day[:4] for day in days}))
    scope = tuple(
        " ".join((event.get(key) or "").casefold().split())
        for key in ("intake", "audience", "method", "clause")
    )
    return event["kind"], year, *scope


def _schedule_conflicts(annotations: list[dict]) -> list[dict]:
    comparisons = defaultdict(dict)
    for item in annotations:
        for event in item["values"].get("events", []):
            scope = _event_scope(event)
            # Explicitly scoped events can be compared across passages of the same source.
            sources = {proof["citation"].split(":", 1)[0] for proof in item["evidence"]}
            boundary = (
                next(iter(sources)) if len(sources) == 1 and any(scope[2:]) else item["target"]
            )
            comparisons[(boundary, scope)].setdefault(_event_time(event), (item["target"], event))
    conflicts = []
    for choices in comparisons.values():
        if len(choices) < 2 or _confirmed_extension([event for _, event in choices.values()]):
            continue
        target, first = next(iter(choices.values()))
        conflicts.append(
            {
                "target": target,
                **{key: first.get(key) for key in ("kind", "intake", "audience", "method")},
                "labels": [event["label"] for _, event in choices.values()],
            }
        )
    return conflicts


def preview(bundle: VersionBundle) -> dict:
    # Keep competing local years/programs local. Only independently corroborated
    # document-wide fields can apply globally; contradictions remain unknown.
    # Schedule events are additive: every proven event is kept, and competing
    # times for one scope are reported instead of being silently dropped.
    fields = defaultdict(dict)
    events = defaultdict(dict)
    for entry in automatic_entries(bundle.content, bundle.documents):
        item = entry["annotation"]
        values = item["values"]
        for event in values.get("events", []):
            events[item["target"]].setdefault(
                digest(event), {"event": event, "evidence": item["evidence"]}
            )
        for field, value in {**values, **values.get("attributes", {})}.items():
            if field in {"attributes", "events"}:
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
    for target, choices in events.items():
        item = grouped.setdefault(target, {"target": target, "values": {}, "evidence": []})
        merged = item["values"].setdefault("events", [])
        known = {digest(event) for event in merged}
        for event_digest, choice in choices.items():
            if event_digest not in known:
                merged.append(choice["event"])
                known.add(event_digest)
            item["evidence"].extend(e for e in choice["evidence"] if e not in item["evidence"])
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
        "conflicts": _schedule_conflicts(annotations),
        "sha256": digest(
            {
                "bundle_sha256": bundle.bundle_sha256,
                "rules_version": RULE_VERSION,
                "annotations": annotations,
            }
        ),
    }
