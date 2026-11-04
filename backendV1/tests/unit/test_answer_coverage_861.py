"""Coverage is structural/declared, never a fabricated semantic-quality score."""

from types import SimpleNamespace

import pytest

from qnu.domains.rag.answer.coverage import assess, plan_for
from qnu.domains.rag.answer.drafting import parse_answer
from qnu.domains.rag.answer.schemas import EvidenceSource, ModelAnswer
from qnu.domains.rag.answer.structure_context import needs_structure, select_groups
from qnu.platform.errors import AppException
from tests.unit.test_rag_clause_context_856 import chunk


def corpus():
    texts = [
        "Article 4. Eligibility conditions",
        "1. Participants must be:",
        "a) Certified technicians;",
        "b) Licensed trainees.",
        "2. All participants must provide:",
        "a) Identification;",
        "b) Training records.",
        "Article 5. Facilities",
        "1. Provide a ventilated room.",
    ]
    rows = [chunk(i, text, i // 4) for i, text in enumerate(texts)]
    docs = [
        {
            "ocr_run_id": "run",
            "pages": [
                {
                    "page_number": 1,
                    "blocks": [
                        {"evidence_id": str(i), "text": text} for i, text in enumerate(texts[:4])
                    ],
                },
                {
                    "page_number": 2,
                    "blocks": [
                        {"evidence_id": str(i + 4), "text": text}
                        for i, text in enumerate(texts[4:])
                    ],
                },
            ],
        }
    ]
    return rows, {"version": SimpleNamespace(documents=docs)}


def sources(rows):
    return [
        EvidenceSource(
            evidence_id=f"E{i + 1}",
            chunk_id=r.id,
            document_id="doc",
            version_id="version",
            publication_decision_id="published",
            score=1,
            text=r.text,
            kind=r.kind,
            citations=r.citations,
            structure=r.structure,
        )
        for i, r in enumerate(rows)
    ]


def test_source_article_crosses_pages_and_compiler_parts_without_next_article():
    rows, bundles = corpus()
    hits = sources([rows[4], rows[0]])
    groups = select_groups(rows, hits, bundles, "Which eligibility conditions apply?")
    assert groups[0]["kind"] == "article"
    assert groups[0]["required_ids"] == [str(i) for i in range(7)]
    assert [u["chunk_ids"] for u in groups[0]["units"]] == [["2"], ["3"], ["5"], ["6"]]
    assert groups[0]["unindexed_refs"] == []


def test_named_bullet_list_keeps_continuations_across_pages_and_stops_at_next_section():
    rows, bundles = corpus()
    texts = [
        "2. Hồ sơ đăng ký:",
        "+ Nộp bản sao giấy tờ",
        "có chữ ký xác nhận.",
        "+ Nộp ảnh thẻ.",
        "Nộp thêm bản giấy khi được yêu cầu.",
        "3. Cách thức xử lý khi đơn vị có nhu cầu bổ sung hồ sơ trong các trường hợp khác",
    ]
    rows = [chunk(i, value, i // 2) for i, value in enumerate(texts)]
    pages = bundles["version"].documents[0]["pages"]
    pages[0]["blocks"] = [{"evidence_id": "0", "text": texts[0]}]
    pages[1]["blocks"] = [
        {"evidence_id": str(i), "text": value} for i, value in enumerate(texts[1:], 1)
    ]
    question = "Cho tôi biết hồ sơ đăng ký"
    hits = sources([rows[3]])
    assert needs_structure(question)
    group = select_groups(rows, hits, bundles, question)[0]
    assert group["required_ids"] == ["0", "1", "2", "3", "4"]
    assert [unit["chunk_ids"] for unit in group["units"]] == [["1"], ["2"], ["3"], ["4"]]
    assert not select_groups(rows, hits, bundles, "Cho tôi biết nộp ảnh thẻ lúc nào")


def test_scope_map_records_unindexed_source_instead_of_claiming_complete():
    rows, bundles = corpus()
    rows.pop(3)
    group = select_groups(rows, sources(rows[:1]), bundles, "Article 4 conditions")[0]
    assert "run:3" in group["unindexed_refs"]
    report = assess(
        ModelAnswer(
            status="answered", statements=[{"text": "Known condition.", "evidence_ids": ["E1"]}]
        ),
        sources(rows),
        {"structure": {"groups": [group]}},
    )
    assert report.status == "partial"
    assert report.structures[0].provided_units < report.structures[0].required_units


def test_no_cross_input_grouping_or_expansion_for_unrelated_reference():
    rows, bundles = corpus()
    foreign = chunk(40, "Foreign terms.", 1)
    foreign.input_id = "other"
    groups = select_groups([*rows, foreign], sources(rows[:1]), bundles, "Article 4 conditions")
    assert "40" not in groups[0]["required_ids"]
    assert not select_groups(rows, sources(rows[:1]), bundles, "Article 99 conditions")


def test_answer_missing_prerequisites_is_partial_even_if_model_claims_covered():
    rows, bundles = corpus()
    group = select_groups(rows, sources(rows[:1]), bundles, "Article 4 conditions")[0]
    src = sources(rows[:7])
    answer = ModelAnswer(
        status="answered",
        statements=[
            {"text": "Provide identification and training records.", "evidence_ids": ["E6", "E7"]}
        ],
        assessment=[{"label": "Conditions", "status": "covered", "evidence_ids": ["E6", "E7"]}],
    )
    report = assess(answer, src, {"structure": {"groups": [group]}})
    assert report.status == "partial"
    assert report.structures[0].cited_units == 2
    assert report.structures[0].required_units == 4


def test_grounded_general_answer_can_expose_missing_details_without_abstaining():
    src = sources(corpus()[0][:1])
    answer = ModelAnswer(
        status="answered",
        statements=[
            {"text": "The operator specifies the application records.", "evidence_ids": ["E1"]}
        ],
        assessment=[
            {"label": "General rule", "status": "covered", "evidence_ids": ["E1"]},
            {"label": "Detailed checklist", "status": "missing", "evidence_ids": ["E1"]},
        ],
    )
    report = assess(answer, src, {})
    assert answer.status == "answered" and report.status == "partial"
    assert report.requirements[1].label == "Detailed checklist"


@pytest.mark.parametrize("ids", [["E999"], ["E1", "E1"]])
def test_coverage_rejects_foreign_or_duplicate_sources(ids):
    src = sources(corpus()[0][:1])
    answer = ModelAnswer(
        status="insufficient_evidence",
        statements=[],
        assessment=[{"label": "Condition", "status": "missing", "evidence_ids": ids}],
    )
    with pytest.raises(AppException, match="phạm vi"):
        assess(answer, src, {})


def test_citation_claim_without_an_answer_does_not_count_as_covered():
    src = sources(corpus()[0][:2])
    answer = ModelAnswer(
        status="answered",
        statements=[{"text": "Known", "evidence_ids": ["E1"]}],
        assessment=[{"label": "Other rule", "status": "covered", "evidence_ids": ["E2"]}],
    )
    report = assess(answer, src, {})
    assert report.status == "partial" and report.requirements[0].status == "missing"


def test_legacy_answers_are_not_relabeled_as_semantically_verified():
    src = sources(corpus()[0][:1])
    answer = parse_answer(
        '{"status":"answered","statements":[{"text":"Known","evidence_ids":["E1"]}]}', src
    )
    assert assess(answer, src, {}).status == "not_assessed"


def test_trimmed_structural_evidence_is_reported_missing_in_the_model_plan():
    rows, bundles = corpus()
    group = select_groups(rows, sources(rows[:1]), bundles, "Article 4 conditions")[0]
    plan = plan_for(sources(rows[:3]), {"structure": {"groups": [group]}})
    assert plan["groups"][0]["unprovided_units"] == 3
    assert plan["scope"] == "retrieved_published_sources_only"


def test_query_about_one_detail_does_not_require_the_entire_unrelated_article():
    rows, bundles = corpus()
    assert not select_groups(rows, sources(rows[:1]), bundles, "Which training records are needed?")


def test_unbounded_list_never_becomes_exhaustive_from_model_self_assessment():
    src = sources(corpus()[0][:1])
    answer = ModelAnswer(
        status="answered",
        statements=[{"text": "Known", "evidence_ids": ["E1"]}],
        assessment=[{"label": "All items", "status": "covered", "evidence_ids": ["E1"]}],
    )
    report = assess(answer, src, {"structure": {"groups": [], "enumeration_requested": True}})
    assert report.status == "partial" and report.scope_status == "unresolved"


def test_article_scope_beats_a_higher_ranked_but_narrower_list():
    rows, bundles = corpus()
    extra = ["Eligibility conditions:", "a) A separate group;", "b) Another group."]
    for index, text in enumerate(extra, len(rows)):
        rows.append(chunk(index, text, 3))
        bundles["version"].documents[0]["pages"][-1]["blocks"].append(
            {"evidence_id": str(index), "text": text}
        )
    groups = select_groups(
        rows, sources([rows[9], rows[4]]), bundles, "Which eligibility conditions apply?"
    )
    assert groups[0]["kind"] == "article" and groups[0]["reference"] == "4"
    assert set(groups[0]["required_ids"]) == {str(i) for i in range(7)}


@pytest.mark.parametrize("change", ["revision", "hash", "run"])
def test_wrong_canonical_identity_cannot_supply_structural_units(change):
    rows, bundles = corpus()
    doc = bundles["version"].documents[0]
    doc["identity"] = {"revision_id": "revision"}
    doc["canonical_sha256"] = "hash"
    locator = rows[3].citations["run:3"]
    locator[{"revision": "revision_id", "hash": "canonical_sha256", "run": "run_id"}[change]] = (
        "other"
    )
    group = select_groups(rows, sources(rows[:1]), bundles, "Article 4 conditions")[0]
    assert "3" not in group["required_ids"] and "run:3" in group["unindexed_refs"]


def test_explicit_multiple_articles_remain_separate_scopes():
    rows, bundles = corpus()
    groups = select_groups(
        rows, sources(rows[:1]), bundles, "List conditions in Article 4 and Article 5"
    )
    assert {g["reference"] for g in groups} == {"4", "5"}
    assert not set(groups[0]["required_ids"]) & set(groups[1]["required_ids"])


def test_article_scope_stops_before_a_separate_appendix():
    rows, bundles = corpus()
    bundle = bundles["version"].documents[0]
    bundle["pages"][-1]["blocks"][3]["text"] = "Appendix A. Forms"
    rows[7].text = "Appendix A. Forms"
    group = select_groups(rows, sources(rows[:1]), bundles, "Article 4 conditions")[0]
    assert set(group["required_ids"]) == {str(i) for i in range(7)}


@pytest.mark.asyncio
async def test_structural_expansion_respects_metadata_before_adding_candidates(monkeypatch):
    from unittest.mock import AsyncMock

    from qnu.domains.knowledge.index.schemas import SearchResponse
    from qnu.domains.rag.answer import context
    from qnu.domains.rag.answer.schemas import AnswerRequest

    rows, bundles = corpus()
    for row in rows:
        row.point_id, row.text_sha256 = row.id, row.id
    primary = sources([rows[4]])
    db = SimpleNamespace(
        get=AsyncMock(
            return_value=SimpleNamespace(
                id="run", status="completed", is_active=True, workspace_id="ws", collection_id="col"
            )
        ),
        scalars=AsyncMock(return_value=SimpleNamespace(all=lambda: rows)),
    )
    monkeypatch.setattr("qnu.domains.knowledge.publication.access.authorize", AsyncMock())
    monkeypatch.setattr(
        context, "_eligible", AsyncMock(return_value=([SimpleNamespace(id="published")], []))
    )
    monkeypatch.setattr(context, "manifest", AsyncMock(return_value={}))
    monkeypatch.setattr(context, "pinned_bundles", AsyncMock(return_value=bundles))
    monkeypatch.setattr(
        context, "matches_metadata", lambda structure, scope: structure != rows[3].structure
    )
    # Give the excluded source a distinct annotation object.
    rows[3].structure = {**rows[3].structure, "annotation": "excluded"}

    async def validated(db, run, allowed, raw, sealed):
        return sources([r for hit in raw for r in rows if r.point_id == hit.point_id])

    monkeypatch.setattr(context, "_hits", validated)
    result = SearchResponse(
        index_run_id="run", generation=1, status="results", hits=primary, eligible_documents=1
    )
    expanded, trace = await context.expand_context(
        db,
        None,
        None,
        "ws",
        "col",
        result,
        AnswerRequest(question="Article 4 conditions", context_max_bytes=32000),
    )
    assert "3" not in {h.chunk_id for h in expanded.hits}
    assert trace["structure"]["groups"][0]["scope_excluded_ids"] == ["3"]
    assert {h.chunk_id for h in expanded.hits} <= {str(i) for i in range(7)}
