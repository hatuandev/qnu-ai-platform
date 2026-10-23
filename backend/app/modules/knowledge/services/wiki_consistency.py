"""Explain deterministic integrity checks separately from semantic uncertainty."""

import asyncio
from collections import defaultdict

from app.core.exceptions import AppException
from app.modules.knowledge.services.automatic_ingestion import content_readiness
from app.modules.knowledge.services.derived_bundle import source_fingerprint
from app.modules.knowledge.services.smart_approval import collect_quality_findings
from app.modules.knowledge.services.source_artifact import get_source_artifact
from app.modules.knowledge.services.wiki_compiler import (
    YEAR,
    digest,
    source_headings,
    source_units,
    structural_context,
    validate_wiki_bundle,
)
from app.modules.knowledge.services.wiki_links import page_references, validate_page_links

CHECK_VERSION = "qnu-wiki-consistency/v1"


def issue(category: str, code: str, message: str, **target) -> dict:
    return {"id": "wikiissue_" + digest([CHECK_VERSION, category, code, target])[:24],
            "category": category, "code": code, "message": message,
            "policy_version": CHECK_VERSION, "target": target, "changes_source_gate": False}


def check_source(source, bundle: dict | None, collection_id: str) -> list[dict]:
    target = {"binding_id": source.binding_id, "source_revision_id": source.id,
              "canonical_hash": source.canonical_hash}
    if bundle is None:
        return [issue("stale", "WIKI_NOT_COMPILED", "Bản nguồn này chưa có trang tri thức.", **target)]
    try:
        validate_wiki_bundle(bundle, source, collection_id)
        units = {unit.id: unit for unit in source_units(source)}
        artifact = get_source_artifact(source)
        source_fingerprint(source, artifact)
    except (AppException, ValueError, KeyError, TypeError) as exc:
        return [issue("blocker", "WIKI_SOURCE_INTEGRITY", "Trang tri thức không còn khớp nguồn; cần đối chiếu bản gốc.",
            **target, reason=(getattr(exc, "details", None) or {}).get("reason", "source_contract"))]
    if bundle["status"] == "unavailable":
        code = bundle.get("failure_code") or "WIKI_UNAVAILABLE"
        category = "stale" if code == "KNOWLEDGE_WIKI_BUDGET" else "provider_infrastructure"
        return [issue(category, code,
                      "Chưa biên soạn được trang tri thức; xem mã lỗi để xử lý.", **target)]
    result = []
    readiness = content_readiness(source)
    for category, key in (("blocker", "blockers"), ("warning", "warnings"), ("source_limitation", "limitations")):
        for finding in (readiness or {}).get(key, []):
            result.append(issue(category, finding.get("reason_code") or "SOURCE_LIMITATION",
                finding.get("message") or "Đối chiếu phạm vi nguồn.", **target, locator=finding))
    if readiness is None:
        quality = {"blockers": [], "warnings": []}
        collect_quality_findings(artifact, quality)
        for category, key in (("blocker", "blockers"), ("warning", "warnings")):
            for finding in quality[key]:
                result.append(issue(category, finding["reason_code"], finding["message"], **target, locator=finding))
    headings = source_headings(list(units.values()))
    for page in bundle["pages"]:
        sections = page["sections"]
        if not any(section["temporal"] for section in sections):
            mentioned = any(YEAR.search(ref["quote"]) for ref in page_references(page))
            result.append(issue("warning" if mentioned else "source_limitation", "YEAR_ROLE_UNKNOWN",
                "Phạm vi năm chưa được xác định; không suy từ tên tệp hoặc ngày ban hành.", **target, page_id=page["id"]))
        signatures = [digest(section) for section in sections]
        if len(signatures) != len(set(signatures)):
            result.append(issue("warning", "DUPLICATE_SECTION", "Có trích đoạn bị lặp trong trang.", **target, page_id=page["id"]))
        for section in sections:
            own = {ref["unit_id"] for ref in section["references"]}
            try:
                required = {u.id for u in structural_context(list(own), units, headings)}
            except AppException:
                result.append(issue("blocker", "SOURCE_CONTEXT_INVALID",
                    "Liên kết ngữ cảnh nguồn không hợp lệ; cần đối chiếu bảng và chú thích.", **target, page_id=page["id"]))
                continue
            if required - own:
                result.append(issue("warning", "NAVIGATION_CONTEXT_INCOMPLETE",
                    "Cần mở cả ngữ cảnh nguồn để giữ điều kiện, ngoại lệ và chú thích.",
                    **target, page_id=page["id"], missing_unit_ids=sorted(required - own)))
    return result


def comparable_values(pages: list[dict], sources: list) -> list[dict]:
    """Differences are review hints: identical code/name is not approved identity.

    Missing data year/metric/unit/qualifiers never forms a contradiction group.
    Different data years or conditions are compared in distinct groups.
    """
    groups = defaultdict(list)
    for source in sources:
        for fact in get_source_artifact(source).get("facts", []):
            raw = fact.get("raw_data") or {}
            temporal = raw.get("temporal_context") or {}
            uid = raw.get("source_unit_id")
            if (temporal.get("status") != "verified" or temporal.get("role", "data") != "data"
                    or not isinstance(temporal.get("year"), int) or not raw.get("unit")
                    or not raw.get("attribute_code") or not raw.get("entity_code")
                    or not any(p["binding_id"] == source.binding_id and uid in
                        {r["unit_id"] for r in page_references(p)} for p in pages)):
                continue
            key = [raw["entity_code"], fact.get("entity_name"), raw["attribute_code"], raw["unit"],
                   temporal["year"], raw.get("row_context"), raw.get("qualifiers"), raw.get("context_unit_ids")]
            groups[digest(key)].append({"binding_id": source.binding_id, "source_revision_id": source.id,
                "unit_id": uid, "value": fact["attribute_value"], "scope": key})
    return [issue("warning", "POSSIBLE_VALUE_CONFLICT",
            "Giá trị khác nhau trong phạm vi tương ứng; đối chiếu đối tượng và nguồn trước khi kết luận mâu thuẫn.",
            evidence=items) for items in groups.values() if len({item["value"] for item in items}) > 1]


async def check_snapshot_consistency(db, snapshot, pages: list[dict], graph: dict) -> list[dict]:
    from app.modules.knowledge.services.wiki_snapshot import snapshot_records

    validate_page_links(graph, pages, snapshot.cache_fingerprint())
    rows = await snapshot_records(db, snapshot, False)
    result = []
    valid_sources = []
    for source, index, _ in rows:
        findings = await asyncio.to_thread(check_source, source, (index.parity_report or {}).get("knowledge_wiki"), snapshot.collection_id)
        result.extend(findings)
        if not any(f["category"] == "blocker" for f in findings):
            valid_sources.append(source)
    result.extend(await asyncio.to_thread(comparable_values, pages, valid_sources))
    for link in graph["links"]:
        if link["status"] == "candidate":
            result.append(issue("candidate", "UNVERIFIED_RELATION",
                "Gợi ý liên kết chưa được xác minh; không dùng làm dữ kiện chắc chắn.", link_id=link["id"], relation=link["relation"]))
        elif link["relation"] == "co_mention":
            result.append(issue("warning", "SHARED_LABEL_NOT_IDENTITY",
                "Các nguồn cùng nhắc tên này; chưa chứng minh cùng một đối tượng.", link_id=link["id"]))
    for page in pages:
        if page["kind"] == "entity" and len({m["code"] for m in page.get("mentions", [])}) > 1:
            result.append(issue("candidate", "AMBIGUOUS_ENTITY_LABEL",
                "Trang nhắc nhiều mã đối tượng; cần đối chiếu trước khi gộp tên hoặc bí danh.", page_id=page["id"]))
    return list({item["id"]: item for item in result}.values())
