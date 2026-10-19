"""Synthetic selector/scope regressions. TEST actors never approve real sources."""
import copy
import json
from types import SimpleNamespace
from unittest.mock import patch

import pytest
from pydantic import ValidationError

import tests.test_semantic_lifecycle as lifecycle
import tests.test_semantic_proposals as fixture
from app.core.exceptions import AppException
from app.modules.knowledge.normalization.qnu_projection import project_document
from app.modules.knowledge.services.semantic_annotations import (
    apply_reviewed_semantics,
    stage_semantic_annotations,
)
from app.modules.knowledge.services.semantic_binding import bind_model_proposals
from app.modules.knowledge.services.semantic_context import ContextBuilder
from app.modules.knowledge.services.semantic_selector import parse_selector
from app.modules.modelops.services.output_contract import (
    OutputContract,
    contract_schemas,
    resolve_contract,
    response_format,
    schema_hash,
)
from tests.test_semantic_context_binding import note_payload

V1, V2 = "qnu_semantic_selector_v1", "qnu_semantic_selector_v2"
pair, storage = lifecycle.pair, lifecycle.storage


def case(text, codes=("AM-0007", "AM-0070")):
    document = fixture.fixture.fixture_document()
    document.blocks[-1].body = text
    rows = [b for b in document.blocks if b.type == "table_row"]
    while len(rows) < len(codes):
        row = copy.deepcopy(rows[-1])
        row.id = f"r{len(rows) + 1}"
        document.blocks.insert(-1, row)
        rows.append(row)
    for row, code in zip(rows, codes, strict=True):
        row.attributes["fields"]["c1"]["raw"] = code
    _, artifact = project_document(document, fixture.fixture.reference(), {})
    packet = ContextBuilder(artifact, document).packets()[0]
    return artifact, packet


def wire(packet, *, version=V1, scope="row", rows=None, contains=None):
    result = note_payload(packet, scope=scope, rows=rows or ["qnu:r1"], columns=[], contains=contains)
    if contains:
        result["notes"][0]["evidence_id"] = min((ev for ev in packet["evidence"]
            if ev["source_unit_id"] == "qnu:g" and contains in ev["text"]), key=lambda ev: len(ev["text"]))["id"]
    if version == V2:
        result["notes"][0].pop("source_unit_id")
    return result


def decision(issue):
    return {"issue_id": issue["issue_id"], "target": issue["target"], "action": "scope_confirmed",
        **issue["review_evidence"][0], "reason": "TEST checked complete source, exact target and exclusion"}


@pytest.mark.parametrize("text,contains,target", [
    ("Chỉ áp dụng AM-0007 và không áp dụng AM-0070.", None, "qnu:r1"),
    ("Áp dụng AM-0007; không áp dụng AM-0070.", "không áp dụng", "qnu:r2"),
])
def test_S01_S02_full_unit_review_not_code_count_or_positive_assumption(text, contains, target):
    artifact, packet = case(text)
    issues = []
    annotations = bind_model_proposals(artifact, packet, wire(packet, rows=[target], contains=contains), review_issues=issues)
    assert len(issues) == 1 and issues[0]["kind"] == "scope_confirmation_required"
    assert issues[0]["review_evidence"][0]["evidence_quote"] == text
    pending = stage_semantic_annotations(artifact, annotations, context_review={"scope": "selected_tables", "issues": issues})
    before = copy.deepcopy(artifact)
    with pytest.raises(AppException) as failure:
        apply_reviewed_semantics(artifact, pending["proposal_hash"], "TEST", "Generic comment")
    assert failure.value.code == "SEMANTIC_CONTEXT_REVIEW_REQUIRED" and artifact == before


@pytest.mark.parametrize("codes,text", [
    (("NV-16", "NV-30"), "Nhóm NV-16 đến NV-30, ngoại trừ NV-20."),
    (("0012", "00027"), "Chỉ mã 0012; ngoại trừ mã 00027."),
    (("AM-0007", "AM-0070"), "Áp dụng điều kiện riêng; cần đối chiếu phạm vi."),
])
def test_S03_S04_group_and_string_codes_are_pending_not_inferred(codes, text):
    artifact, packet = case(text, codes)
    issues = []
    annotations = bind_model_proposals(artifact, packet, wire(packet, scope="group"), review_issues=issues)
    assert issues and annotations.notes[0].row_unit_ids == ["qnu:r1"]
    assert [row[0]["raw"] for row in artifact["tables"][0]["row_fields"]] == list(codes)
    assert issues[0]["target"]["row_unit_ids"] == ["qnu:r1"]


def test_S03_range_exception_never_enters_confirmed_target_set():
    artifact, packet = case("Nhóm NV-16 đến NV-30, ngoại trừ NV-20.", ("NV-16", "NV-30", "NV-20"))
    issues = []
    annotations = bind_model_proposals(artifact, packet, wire(packet, scope="group", rows=["qnu:r1", "qnu:r2"]), review_issues=issues)
    pending = stage_semantic_annotations(artifact, annotations, context_review={"scope": "selected_tables", "issues": issues})
    applied = apply_reviewed_semantics(artifact, pending["proposal_hash"], "TEST", "TEST excludes NV-20", context_decisions=[decision(issues[0])])
    units = {u["id"]: u for u in applied["retrieval_units"]["units"]}
    assert all("qnu:g" in units[row]["context_refs"] for row in ["qnu:r1", "qnu:r2"])
    assert "qnu:g" not in units["qnu:r3"]["context_refs"]


def test_S05_specific_review_does_not_spread_to_excluded_row():
    text = "Chỉ áp dụng AM-0007 và không áp dụng AM-0070."
    artifact, packet = case(text)
    issues = []
    annotations = bind_model_proposals(artifact, packet, wire(packet), review_issues=issues)
    pending = stage_semantic_annotations(artifact, annotations, context_review={"scope": "selected_tables", "issues": issues})
    applied = apply_reviewed_semantics(artifact, pending["proposal_hash"], "TEST-reviewer", "TEST exact scope", context_decisions=[decision(issues[0])])
    units = {u["id"]: u for u in applied["retrieval_units"]["units"]}
    assert "qnu:g" in units["qnu:r1"]["context_refs"]
    assert "qnu:g" not in units["qnu:r2"]["context_refs"]
    from app.modules.knowledge.services.semantic_context_review import proposal_summary
    assert proposal_summary(applied["semantic_annotations"])["publication_blocked"]


@pytest.mark.parametrize("mutation", ["target", "issue", "actor", "partial", "hash"])
def test_S06_specific_decision_cannot_be_forged(mutation):
    artifact, packet = case("Chỉ áp dụng AM-0007; không áp dụng AM-0070.")
    issues = []
    annotations = bind_model_proposals(artifact, packet, wire(packet, contains="không áp dụng", rows=["qnu:r2"]), review_issues=issues)
    pending = stage_semantic_annotations(artifact, annotations, context_review={"issues": issues})
    intent = decision(issues[0]); digest = pending["proposal_hash"]
    if mutation == "target": intent["target"]["row_unit_ids"] = ["qnu:r1"]
    if mutation == "issue": intent["issue_id"] = "unrelated"
    if mutation == "actor": intent["actor_id"] = "forged"
    if mutation == "partial":
        selected = annotations.notes[0]
        intent.update(evidence_binding=selected.evidence_binding.model_dump(), evidence_quote=selected.evidence_quote)
    if mutation == "hash": digest = "0" * 64
    with pytest.raises((ValueError, AppException)):
        apply_reviewed_semantics(artifact, digest, "TEST", "TEST negative", context_decisions=[intent])


def test_S_scope_collector_and_full_review_source_are_required():
    artifact, packet = case("Chỉ áp dụng AM-0007; không áp dụng AM-0070.")
    with pytest.raises(ValueError, match="COLLECTOR_REQUIRED"):
        bind_model_proposals(artifact, packet, wire(packet))
    artifact, packet = case("AM-0007 " + "nguồn " * 1800)
    with pytest.raises(ValueError, match="FULL_SOURCE_REVIEW_UNAVAILABLE"):
        bind_model_proposals(artifact, packet, wire(packet), review_issues=[])


@pytest.mark.parametrize("version", [V1, V2])
def test_B01_B04_expected_contract_derives_same_verified_annotation(version):
    artifact, packet = case("Điều kiện nguồn đầy đủ cho bảng này.")
    payload = wire(packet, version=version, scope="table")
    payload["notes"][0]["row_unit_ids"] = []
    annotations = bind_model_proposals(artifact, packet, payload, selector_contract=version)
    assert annotations.notes[0].note_unit_id == "qnu:g"
    assert annotations.notes[0].evidence_binding.source_unit_id == "qnu:g"
    assert annotations.notes[0].evidence_quote == "Điều kiện nguồn đầy đủ cho bảng này."


@pytest.mark.parametrize("mutation", ["owner", "missing"])
def test_B02_B03_v1_never_recovers_wrong_or_missing_owner(mutation):
    artifact, packet = case("Điều kiện nguồn đầy đủ cho bảng này.")
    payload = wire(packet, scope="table")
    if mutation == "owner": payload["notes"][0]["source_unit_id"] = "qnu:r1"
    else: payload["notes"][0].pop("source_unit_id")
    with pytest.raises((ValueError, ValidationError)):
        bind_model_proposals(artifact, packet, payload)


@pytest.mark.parametrize("extra", ["source_unit_id", "evidence_quote", "approval"])
def test_B05_v2_cannot_send_owner_quote_or_approval(extra):
    _, packet = case("Điều kiện nguồn đầy đủ cho bảng này.")
    payload = wire(packet, version=V2, scope="table")
    payload["notes"][0][extra] = "forged"
    with pytest.raises(AppException) as failure:
        parse_selector(SimpleNamespace(content=json.dumps(payload)), "prompt_only", expected_contract=V2)
    assert failure.value.details["stage"] == "selector_schema"


@pytest.mark.parametrize("mutation", ["unknown_id", "registry_key", "revision", "span", "text_hash", "target_row", "target_table", "registry_only", "public_owner"])
def test_B07_B08_v2_keeps_packet_and_canonical_source_guards(mutation):
    artifact, packet = case("Điều kiện nguồn đầy đủ cho bảng này.")
    payload = wire(packet, version=V2)
    item = payload["notes"][0]; binding = packet["_bindings"][item["evidence_id"]]
    if mutation == "unknown_id": item["evidence_id"] = "ev:other-packet"
    if mutation == "registry_key": binding["evidence_id"] = "ev:alias"
    if mutation == "revision": binding["source_identity"]["revision_id"] = "other"
    if mutation == "span": binding["end"] += 9999
    if mutation == "text_hash": binding["text_sha256"] = "0" * 64
    if mutation == "target_row": item["row_unit_ids"] = ["qnu:foreign"]
    if mutation == "target_table": item["table_id"] = "foreign-table"
    if mutation == "registry_only": packet["evidence"] = [e for e in packet["evidence"] if e["id"] != item["evidence_id"]]
    if mutation == "public_owner": next(e for e in packet["evidence"] if e["id"] == item["evidence_id"])["source_unit_id"] = "qnu:r1"
    with pytest.raises(ValueError):
        bind_model_proposals(artifact, packet, payload, selector_contract=V2, review_issues=[])


def test_C01_schema_cache_and_provider_trace_pin_each_version():
    traces = []
    for version in [V1, V2, V1, V2]:
        contract = OutputContract(name=version)
        metadata = resolve_contract(contract, {"json_schema_supported": True}, supports_chat_schema=True)
        schema = response_format(metadata)["json_schema"]["schema"]
        assert metadata["schema_hash"] == schema_hash(contract_schemas(version)[1])
        assert schema == contract_schemas(version)[1]
        assert metadata["version"] == (1 if version == V1 else 2)
        traces.append(metadata["schema_hash"])
    assert traces[0] == traces[2] != traces[1] == traces[3]


@pytest.mark.parametrize("metadata", [
    {"name": V1, "version": 1}, {"name": V2, "version": 1},
    {"name": V2, "version": 2, "schema_hash": "wrong"},
])
def test_B06_response_cannot_change_pinned_contract(metadata):
    _, packet = case("Điều kiện nguồn đầy đủ cho bảng này.")
    response = SimpleNamespace(content=json.dumps(wire(packet, version=V2)), output_contract=metadata)
    with pytest.raises(AppException):
        parse_selector(response, "prompt_only", expected_contract=V2)


@pytest.mark.asyncio
async def test_C02_real_pipeline_v2_syntax_retry_stays_same_contract_and_stages_once(pair):
    from app.modules.knowledge.services.qnu_serving import verify_revision_pair
    from app.modules.knowledge.services.semantic_annotations import (
        stage_semantic_annotations as stage,
    )
    from app.modules.knowledge.services.semantic_modelops import generate_bound_semantics
    artifact = lifecycle.artifact_of(pair); calls = []
    async def generate(_db, request):
        calls.append(request)
        packet = json.loads(request.messages[1].content)
        data = wire(packet, version=V2, scope="column", rows=[])
        data["notes"][0].update(row_unit_ids=[], column_ids=["c4"])
        return SimpleNamespace(content="bad json" if len(calls) == 1 else json.dumps(data), provider="TEST", model="TEST",
            is_fallback=False, prompt_tokens=1, completion_tokens=1, cost_usd=0)
    with patch("app.modules.modelops.service.modelops_service.generate", side_effect=generate), patch(
        "app.modules.knowledge.services.semantic_annotations.stage_semantic_annotations", wraps=stage) as staging:
        pending = await generate_bound_semantics(None, artifact, "TEST", "TEST", "TEST", document=await verify_revision_pair(pair))
    assert len(calls) == 2 and staging.call_count == 1
    assert calls[0].messages[1].content == calls[1].messages[1].content
    assert calls[0].output_contract == calls[1].output_contract and calls[0].output_contract.name == V2
    assert pending["status"] == "proposed" and not artifact.get("semantic_effective")


@pytest.mark.asyncio
async def test_B09_v2_cells_and_limitations_keep_raw_and_known_unknown_guards(pair):
    from app.modules.knowledge.services.qnu_serving import verify_revision_pair
    artifact = lifecycle.artifact_of(pair)
    packet = ContextBuilder(artifact, await verify_revision_pair(pair)).packets()[0]
    data = wire(packet, version=V2, scope="column")
    data["notes"][0].update(row_unit_ids=[], column_ids=["c4"])
    cell = next(e for e in packet["evidence"] if e["source_unit_id"] == "qnu:r1" and e["column_id"] == "c7")
    prose = next(e for e in packet["evidence"] if e["source_unit_id"] == "qnu:g")
    data["cells"] = [{"evidence_id": cell["id"], "reason": "TEST literal unpublished source", "row_unit_id": "qnu:r1", "column_id": "c7", "state": "not_stated"}]
    data["limitations"] = [{"evidence_id": prose["id"], "reason": "TEST unknown remains unknown pending review", "row_unit_id": "qnu:r2", "column_id": "c7",
        "basis": "human_examined_scope", "examined_unit_ids": [u["id"] for u in packet["units"]] + [r["id"] for t in packet["tables"] for r in t["rows"]]}]
    annotations = bind_model_proposals(artifact, packet, data, selector_contract=V2, review_issues=[])
    assert annotations.cells[0].raw == "Not published yet"
    assert annotations.limitations[0].raw == "/"
    pending = stage_semantic_annotations(artifact, annotations)
    assert pending["status"] == "proposed"
    assert artifact["tables"][0]["row_fields"][1][6]["state"] == "ambiguous"
    assert annotations.cells[0].evidence_unit_id == "qnu:r1" and annotations.limitations[0].evidence_unit_id == "qnu:g"


@pytest.mark.asyncio
async def test_L03_L04_row_scope_decisions_survive_fresh_storage_rebuild_and_rejection(pair, storage):
    from app.modules.knowledge.services.qnu_serving import verify_revision_pair
    from app.modules.knowledge.services.semantic_store import (
        STORE,
        proposal_base,
        rebuild_projection,
        record_decision,
        semantic_fingerprint,
    )
    artifact = lifecycle.artifact_of(pair)
    packet = ContextBuilder(artifact, await verify_revision_pair(pair)).packets()[0]
    issues = []
    annotations = bind_model_proposals(artifact, packet, wire(packet, version=V2), selector_contract=V2, review_issues=issues)
    pending = stage_semantic_annotations(artifact, annotations, context_review={"scope": "selected_tables", "issues": issues})
    pair.parse_provenance = {**pair.parse_provenance, "structured_artifact": artifact}
    await record_decision(pair, artifact, pending["proposal_hash"], "TEST-reviewer552", "TEST exact first row, excluded second", "approved", context_decisions=[decision(issues[0])])
    active = copy.deepcopy(pair.parse_provenance[STORE]["active"])
    from app.modules.knowledge.models import KnowledgeSourceRevision
    fresh = KnowledgeSourceRevision(**{c.name: copy.deepcopy(getattr(pair, c.name)) for c in pair.__table__.columns})
    with patch("app.modules.modelops.service.modelops_service.generate", side_effect=AssertionError("Rebuild must not call LLM")):
        hashes = []
        for _ in range(3):
            _, restored = await rebuild_projection(fresh)
            hashes.append(semantic_fingerprint(restored))
            units = {u["id"]: u for u in restored["retrieval_units"]["units"]}
            assert "qnu:g" in units["qnu:r1"]["context_refs"] and "qnu:g" not in units["qnu:r2"]["context_refs"]
            assert restored["semantic_annotations"]["review"]["context_decisions"][0]["target"] == issues[0]["target"]
        assert len(set(hashes)) == 1
    base = await proposal_base(fresh, restored)
    newer = stage_semantic_annotations(restored, annotations, base_artifact=base, context_review={"scope": "selected_tables", "issues": issues})
    fresh.parse_provenance = {**fresh.parse_provenance, "structured_artifact": restored}
    await record_decision(fresh, restored, newer["proposal_hash"], "TEST-reviewer552", "TEST excluded target must be changed", "changes_requested")
    assert fresh.parse_provenance[STORE]["active"] == active
    _, replayed = await rebuild_projection(fresh)
    assert replayed["semantic_annotations"]["status"] == "changes_requested"
    fresh.origin_file_hash = "f" * 64
    with pytest.raises(AppException):
        await rebuild_projection(fresh)


@pytest.mark.asyncio
@pytest.mark.parametrize("version", [V1, V2])
async def test_C01_actual_modelops_fallback_keeps_wire_contract(monkeypatch, version):
    import httpx

    from app.modules.modelops.schemas import ChatMessage, LLMGenerateRequest
    from tests.test_json_output_contract import inference_boundary, install_http
    requests = []
    def server(request):
        requests.append(json.loads(request.content))
        return httpx.Response(200, json={"choices": [{"message": {"content": "{}"}, "finish_reason": "stop"}]})
    install_http(monkeypatch, server)
    service, db = inference_boundary(monkeypatch, [{}, {"json_schema_supported": True}])
    result = await service.generate(db, LLMGenerateRequest(messages=[ChatMessage(role="user", content="TEST output contract")],
        preferred_provider_id="contract-test-0", preferred_model_name="alias0", fallback_provider_id="contract-test-1", fallback_model_name="alias1",
        output_contract=OutputContract(name=version)))
    assert result.is_fallback and len(requests) == 1
    assert requests[0]["response_format"]["json_schema"]["name"] == version
    assert result.output_contract["schema_hash"] == schema_hash(contract_schemas(version)[1])
    assert result.attempt_trace[0]["code"] == "MODEL_OUTPUT_CONTRACT_UNSUPPORTED"


def test_S08_v2_duplicate_text_keeps_distinct_owners_and_tables():
    document = fixture.fixture.fixture_document()
    document.blocks[-1].body = "Identical condition source text."
    original_table = next(b for b in document.blocks if b.id == "t")
    source_note = next(b for b in document.blocks if b.id == "g")
    twin = original_table.model_copy(deep=True, update={"id": "twin"})
    document.blocks.append(twin)
    for row in [b for b in list(document.blocks) if b.type == "table_row"]:
        document.blocks.append(row.model_copy(deep=True, update={"id": row.id + "twin", "parent_id": "twin"}))
    document.blocks.append(source_note.model_copy(deep=True, update={"id": "g-twin"}))
    _, artifact = project_document(document, fixture.fixture.reference(), {})
    packets = ContextBuilder(artifact, document).packets()
    notes = []
    for table_id, owner in [("qnu:t", "qnu:g"), ("qnu:twin", "qnu:g-twin")]:
        packet = next(p for p in packets if any(t["id"] == table_id for t in p["tables"]))
        payload = note_payload(packet, owner, table_id=table_id, scope="table", columns=[])
        payload["notes"][0].pop("source_unit_id")
        notes.append(bind_model_proposals(artifact, packet, payload, selector_contract=V2).notes[0])
    assert notes[0].evidence_quote == notes[1].evidence_quote
    assert notes[0].note_unit_id != notes[1].note_unit_id and notes[0].table_id != notes[1].table_id
    assert notes[0].evidence_binding.evidence_id != notes[1].evidence_binding.evidence_id
