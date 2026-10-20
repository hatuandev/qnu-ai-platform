"""Evidence-bound answers to year-specific table questions; no model synthesis."""

from __future__ import annotations

import json
import re
from decimal import Decimal, InvalidOperation
from typing import Any

from app.modules.knowledge.entity_codes import code_candidates, normalize_code
from app.modules.knowledge.metric_roles import header_unit
from app.modules.knowledge.services.source_artifact import cell_context
from app.modules.knowledge.services.temporal_metadata import YEAR
from app.modules.rag.query_constraints import metric_attributes, source_name_in_question
from app.modules.rag.query_constraints import requested_unit as query_unit
from app.modules.rag.query_router import query_classifier

CONTRACT_VERSION = "temporal-table-v1"
METRIC_ATTRIBUTES = {"cutoff_score", "expected_quota", "tuition_fee", "subject_combinations", "converted_score",
                     "reported_count", "estimated_count", "rate"}


def is_temporal_table_question(question: str, module_code: str) -> bool:
    analysis = query_classifier.analyze(question, module_code=module_code)
    return bool((YEAR.search(question) and (METRIC_ATTRIBUTES.intersection(analysis.fact_attributes) or metric_attributes(question)))
                or (code_candidates(question) and METRIC_ATTRIBUTES.intersection(analysis.fact_attributes))
                or (YEAR.search(question) and analysis.is_fact_first and
                    (analysis.target_entities or analysis.entity_codes))
                or "converted_score" in analysis.fact_attributes)


def _record(fact: Any) -> dict[str, Any]:
    if isinstance(fact, dict):
        return fact
    return {key: getattr(fact, key, None) for key in
            ("id", "entity_name", "entity_code", "attribute_name", "attribute_value", "raw_data", "binding_id", "index_revision_id")}


def _escape(value: Any) -> str:
    return str(value if value is not None else "—").replace("|", "\\|").replace("\n", " ")


def decide_table_answer(question: str, facts: list[Any], *, module_code: str = "admissions",
                        requested_metric: str | None = None, requested_unit: str | None = None,
                        requested_metrics: list[str] | None = None,
                        source_entity_codes: list[str] | None = None,
                        source_entity_names: list[str] | None = None) -> dict[str, Any] | None:
    """Unknown/ambiguous contexts never borrow the document's subject or issue year.

    Only handles explicit single-year table metrics. Other temporal roles require
    a separate verified evidence path; absence here is not a publication claim.
    """
    analysis = query_classifier.analyze(question, module_code=module_code)
    years = sorted({int(year) for year in YEAR.findall(question)})
    attributes = analysis.fact_attributes
    attributes = [attribute for attribute in attributes if attribute in METRIC_ATTRIBUTES]
    explicit_metrics = requested_metrics or metric_attributes(question)
    if explicit_metrics:
        attributes = list(dict.fromkeys([a for a in explicit_metrics if a in METRIC_ATTRIBUTES]))
    if requested_metric in METRIC_ATTRIBUTES:
        attributes = [requested_metric]
    unit = requested_unit or query_unit(question)
    conversion = "converted_score" in attributes
    if not attributes and not re.search(r'\b(?:số lượng|bao nhiêu|quantity|count)\b', question, re.IGNORECASE):
        return None
    if (not attributes and not code_candidates(question)) or (not years and not conversion and not code_candidates(question)):
        return None
    requested = {"years": years, "attributes": attributes, "entities": analysis.target_entities,
                 "entity_codes": analysis.entity_codes}
    decision = {"version": CONTRACT_VERSION, "requested": requested, "matched_fact_ids": [], "claim_bindings": []}
    if not attributes:
        return {**decision, 'status': 'missing', 'reason': 'METRIC_UNVERIFIED',
                'answer': 'Cần xác định đại lượng được hỏi: chỉ tiêu, số ghi nhận hoặc đại lượng khác được nguồn định nghĩa.'}
    if not years and not conversion:
        return {**decision, 'status': 'missing', 'reason': 'DATA_YEAR_REQUIRED',
                'answer': 'Cần xác định năm dữ liệu trước khi chọn số liệu của mã được hỏi.'}
    if re.search(r"\b(?:19|20)\d{2}\s*[–—-]\s*(?:19|20)\d{2}\b", question):
        return {**decision, "status": "ambiguous", "reason": "INTERVAL_REQUIRES_PERIOD_EVIDENCE",
                "answer": "Câu hỏi yêu cầu một khoảng năm. Cần đối chiếu đầy đủ các kỳ trong khoảng; mình chưa có đủ căn cứ để trả lời toàn khoảng."}
    matches = []
    unscoped = []
    for original in facts:
        fact = _record(original)
        raw = fact.get("raw_data") or {}
        if raw.get('field_state') not in {None, 'present'} or raw.get('context_ambiguous'):
            continue
        if raw.get("context_review") and raw["context_review"].get("status") != "verified":
            continue
        context = raw if raw.get("temporal_context") else {**raw, **cell_context(fact["attribute_name"] or "")}
        temporal = context.get("temporal_context") or {}
        if not conversion and (temporal.get('status') in {'ambiguous', 'unknown'} or temporal.get('role') not in {None, 'data'}):
            unscoped.append(fact['id'])
            continue
        relation = raw.get("relation") or {}
        if conversion:
            inputs = [number for number in re.findall(r"\b\d+(?:[.,]\d+)?\b", question) if not YEAR.fullmatch(number)]
            if relation.get("type") != "numeric_mapping" or len(inputs) != 1 or not relation.get("input_label"):
                continue
            identifiers = re.findall(r"\b[A-Z][A-Z0-9]{1,}\b", relation["input_label"])
            label_matches = relation["input_label"].casefold() in question.casefold() or (
                identifiers and all(re.search(r"\b" + re.escape(token) + r"\b", question, re.IGNORECASE) for token in identifiers))
            if not label_matches:
                continue
            try:
                if Decimal(inputs[0].replace(",", ".")) != Decimal(relation["input_value"].replace(",", ".")):
                    continue
            except InvalidOperation:
                continue
            context = {**context, "attribute_code": "converted_score"}
        if context.get("attribute_code") not in attributes:
            continue
        name = (fact.get("entity_name") or "").casefold()
        code = normalize_code(str(fact.get('entity_code') or raw.get("entity_code") or raw.get("major_code") or ""))
        codes = [normalize_code(c) for c in (code_candidates(question) or source_entity_codes or [])
                 if c != 'certificate_conversion']
        names = source_entity_names or analysis.target_entities
        if conversion:
            pass  # The label + numeric input were matched above, not a loose entity substring.
        elif codes or names:
            if not (code in codes if codes else any(n.casefold() in name for n in names)):
                continue
        else:
            # Never bind a metric from an unrelated row on attribute similarity alone.
            if len(name.split()) < 2 or not source_name_in_question(name, question):
                continue
        if years and (temporal.get("type") != "year" or temporal.get("year") not in years):
            if temporal.get("type") in {None, "unknown"}:
                unscoped.append(fact["id"])
            continue
        if unit:
            if context.get('attribute_code') == 'cutoff_score':
                if normalize_code(str((context.get('qualifiers') or {}).get('method') or '')) != normalize_code(unit):
                    continue
            elif normalize_code(str(context.get('unit') or header_unit(fact['attribute_name'] or '') or '')) != normalize_code(unit):
                continue
        matches.append({**fact, "raw_data": context})
    if not matches:
        if unscoped:
            return {**decision, "status": "missing", "reason": "DATA_YEAR_UNVERIFIED",
                    "unscoped_fact_ids": unscoped,
                    "answer": "Mình tìm thấy dữ liệu liên quan, nhưng chưa xác minh được năm áp dụng "
                              "của các bản ghi này. Vì vậy, mình chưa thể khẳng định chúng đúng cho năm "
                              + ", ".join(map(str, years)) + "."}
        return {**decision, "status": "missing", "reason": "NO_COMPATIBLE_FACT_EVIDENCE",
                "answer": "Trong kho tài liệu đã xuất bản, mình chưa tìm thấy căn cứ đủ rõ cho số liệu và ngữ cảnh được hỏi. Không thể dùng số liệu năm hoặc điều kiện khác thay thế."}
    if len({(f.get('binding_id'), f.get('index_revision_id')) for f in matches}) > 1:
        return {**decision, 'status': 'ambiguous', 'reason': 'ENTITY_SCOPE_AMBIGUOUS',
                'answer': 'Mã được hỏi xuất hiện trong nhiều nguồn hoặc phạm vi. Cần xác định rõ nguồn trước khi chọn số liệu.'}
    if not unit and len({f['raw_data'].get('unit') for f in matches}) > 1:
        return {**decision, 'status': 'ambiguous', 'reason': 'UNIT_SCOPE_AMBIGUOUS',
                'answer': 'Có nhiều đơn vị cho đại lượng được hỏi. Cần xác định đơn vị trước khi chọn số liệu.'}
    tuples: dict[tuple, set[str]] = {}
    for fact in matches:
        method = (fact["raw_data"].get("qualifiers") or {}).get("method")
        raw = fact['raw_data']
        key = (raw.get('entity_code') or fact["entity_name"], raw["attribute_code"],
               raw.get("temporal_context", {}).get("year"), raw.get('unit'),
               json.dumps(raw.get('qualifiers') or {}, sort_keys=True))
        tuples.setdefault(key, set()).add(fact["attribute_value"])
    if any(len(values) > 1 for values in tuples.values()):
        return {**decision, "status": "conflict", "reason": "CONFLICTING_VALUES",
                "answer": "Các bằng chứng cùng ngữ cảnh đang có giá trị khác nhau. Cần kiểm tra nguồn trước khi trả lời."}
    lines = ["| Thực thể | Thuộc tính | Năm | Phương thức | Giá trị |", "| --- | --- | --- | --- | --- |"]
    for fact in matches:
        raw = fact["raw_data"]
        year = raw.get("temporal_context", {}).get("year")
        method = (raw.get("qualifiers") or {}).get("method")
        lines.append("| " + " | ".join(_escape(v) for v in
                     (fact["entity_name"], fact["attribute_name"], year, method, fact["attribute_value"])) + " |")
        decision["claim_bindings"].append({"fact_id": fact["id"], "entity": fact["entity_name"],
                "attribute": raw["attribute_code"], "year": year, "method": method,
                "value": fact["attribute_value"], "source_revision_id": raw.get("source_revision_id"),
                "page_number": raw.get("page_number")})
    covered = {(claim["attribute"], claim["year"]) for claim in decision["claim_bindings"]}
    missing = [{"attribute": attribute, "year": year} for attribute in attributes for year in years
               if (attribute, year) not in covered]
    requested_codes = code_candidates(question)
    if len(requested_codes) > 1:
        coordinates = {(normalize_code(f.get('entity_code') or (f.get('raw_data') or {}).get('entity_code') or ''),
                        f['raw_data']['attribute_code'], f['raw_data'].get('temporal_context', {}).get('year')) for f in matches}
        missing = [{'entity_code': code, 'attribute': attribute, 'year': year}
                   for code in requested_codes for attribute in attributes for year in years
                   if (code, attribute, year) not in coordinates]
    for item in missing:
        lines.append(f"| — | {_escape(item['attribute'])} | {item['year']} | — | Chưa đủ căn cứ |")
    return {**decision, "status": "missing" if missing else "supported", "reason": "PARTIAL_COVERAGE" if missing else "EXACT_FACT_CONTEXT",
            "missing_constraints": missing, "answer": "\n".join(lines),
            "matched_fact_ids": [fact["id"] for fact in matches], "facts": matches}
