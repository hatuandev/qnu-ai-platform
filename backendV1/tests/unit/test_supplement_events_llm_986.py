import json

import pytest

from qnu.domains.knowledge.compilation import segments as split
from qnu.domains.knowledge.compilation import supplement
from qnu.platform.errors import AppException

QUOTE = "Lịch công bố kết quả: 15/8/2026. Thí sinh kiểm tra trên cổng."


def documents():
    return [
        {
            "ocr_run_id": "ocr",
            "pages": [
                {
                    "page_number": 1,
                    "blocks": [
                        {"evidence_id": "ev1", "text": QUOTE, "type": "paragraph"},
                        {
                            "evidence_id": "ev2",
                            "text": "Hạn đăng ký: 30/6/2026",
                            "type": "paragraph",
                        },
                    ],
                }
            ],
        }
    ]


def draft():
    return {
        "title": "Thông báo",
        "sections": [{"heading": "A", "paragraphs": [{"text": QUOTE, "citations": ["ocr:ev1"]}]}],
        "unknowns": [],
        "citations": {"ocr:ev1": {"page": 1}},
        "source_tables": [],
    }


def content(citation="ocr:ev1", kind="result_date"):
    return json.dumps(
        {
            "sections": [{"heading": "A", "paragraphs": [{"text": "x", "citations": ["ocr:ev1"]}]}],
            "unknowns": [],
            "metadata": [],
            "events": [
                {
                    "event": {
                        "kind": kind,
                        "label": "Lịch công bố kết quả",
                        "moment": {"date": "2026-08-15"},
                    },
                    "citation": citation,
                    "quote": QUOTE,
                    "scope": "local",
                }
            ],
        },
        ensure_ascii=False,
    )


def test_valid_event_proposal_parses_and_serializes_dates():
    parsed = split.parse_segment_draft(content(), {"ocr:ev1"}, split.PROJECTION_SUPPLEMENT)
    assert parsed["events"][0]["event"]["moment"]["date"] == "2026-08-15"
    assert json.loads(json.dumps(parsed))["events"] == parsed["events"]


def test_invalid_optional_metadata_keeps_valid_proposals_and_content():
    payload = json.loads(content())
    metadata = {"field": "data_year", "value": 2026, "citation": "ocr:ev1", "quote": QUOTE}
    payload["metadata"] = [metadata, {**metadata, "value": [2024, 2025]}]
    parsed = split.parse_segment_draft(json.dumps(payload), {"ocr:ev1"}, split.PROJECTION_SELECTIVE)
    assert parsed["metadata"] == [{**metadata, "scope": "local"}]
    assert parsed["rejected_metadata_proposals"] == 1
    assert parsed["events"][0]["event"]["moment"]["date"] == "2026-08-15"
    assert parsed["sections"] == payload["sections"]

    payload["sections"][0]["paragraphs"][0]["citations"] = ["ocr:ev2"]
    with pytest.raises(AppException) as error:
        split.parse_segment_draft(json.dumps(payload), {"ocr:ev1"}, split.PROJECTION_SELECTIVE)
    assert error.value.code == "compilation_citation_invalid"


def test_model_cannot_promote_a_year_from_a_hypothetical_clause():
    quote = "tuyển sinh năm 2027"
    text = f"Chỉ tiêu là dữ liệu của năm 2026. Khi người dùng hỏi về {quote}, hãy đối chiếu nguồn."
    sources = documents()
    sources[0]["pages"][0]["blocks"][0]["text"] = text
    parsed = draft()
    part = {
        "sections": [],
        "unknowns": [],
        "metadata": [
            {"field": "data_year", "value": 2027, "citation": "ocr:ev1", "quote": quote},
        ],
    }
    result = supplement.attach(parsed, sources, [(1, part)], "a" * 64, {})
    years = {x["annotation"]["values"].get("data_year") for x in result["supplement"]["metadata"]}
    assert 2026 in years
    assert 2027 not in years


@pytest.mark.parametrize(
    "payload,code",
    [
        (content(citation="ocr:ev2"), "compilation_citation_invalid"),
        (content(kind="school_start_date"), "compilation_draft_invalid"),
    ],
)
def test_out_of_part_citation_or_unsupported_kind_is_rejected(payload, code):
    with pytest.raises(AppException) as caught:
        split.parse_segment_draft(payload, {"ocr:ev1"}, split.PROJECTION_SUPPLEMENT)
    assert caught.value.code == code


def test_prompt_versions_and_event_contract_move_together():
    assert split.PROMPT_VERSIONS[split.PROJECTION_SUPPLEMENT].endswith("/v3")
    assert split.PROMPT_VERSIONS[split.PROJECTION_SELECTIVE].endswith("/v3")
    prompt = split.segment_system(1, 1, projection=split.PROJECTION_SUPPLEMENT)
    assert '"events"' in prompt and "registration_deadline" in prompt
    assert "document" in prompt


def test_segment_schema_exposes_the_event_contract():
    schema = split.segment_schema({"ocr:ev1": {"page": 1}}, split.PROJECTION_SUPPLEMENT)
    encoded = json.dumps(schema, ensure_ascii=False)
    assert '"events"' in encoded
    assert "registration_deadline" in encoded


def part(proposals):
    return {"sections": [], "unknowns": [], "metadata": [], "events": proposals}


def proposal(quote=QUOTE, citation="ocr:ev1"):
    return {
        "event": {
            "kind": "result_date",
            "label": "Lịch công bố kết quả",
            "moment": {"date": "2026-08-15"},
        },
        "citation": citation,
        "quote": quote,
        "scope": "local",
    }


def test_owned_events_keep_only_quotes_inside_the_owned_citation():
    kept = supplement.owned_events(
        part(
            [
                proposal(),
                proposal(quote="Hạn đăng ký: 30/6/2026"),
                proposal(citation="ocr:ghost"),
            ]
        ),
        documents(),
    )
    assert kept == [proposal()]


def test_model_event_becomes_a_proposed_annotation_for_its_paragraph():
    attached = supplement.attach(
        draft(), documents(), [(0, part([proposal()]))], "a" * 64, {"ai_supplement": True}
    )
    entries = [
        entry
        for entry in attached["supplement"]["metadata"]
        if entry["origin"] == "model" and entry["annotation"]["values"].get("events")
    ]
    assert [(entry["annotation"]["target"], entry["segment"]) for entry in entries] == [
        ("paragraph:0:0", 0)
    ]
    assert entries[0]["annotation"]["values"]["events"][0]["kind"] == "result_date"


def test_unproven_model_event_is_not_stored():
    attached = supplement.attach(
        draft(),
        documents(),
        [(0, part([proposal(quote="Hạn đăng ký: 15/10/2026")]))],
        "a" * 64,
        {"ai_supplement": True},
    )
    assert not [
        entry
        for entry in attached["supplement"]["metadata"]
        if entry["origin"] == "model" and entry["annotation"]["values"].get("events")
    ]


def test_attached_model_event_reaches_preview_for_the_cited_paragraph():
    from qnu.domains.knowledge.publication.automatic_metadata import preview
    from qnu.domains.knowledge.publication.evidence import VersionBundle

    attached = supplement.attach(
        draft(), documents(), [(0, part([proposal()]))], "a" * 64, {"ai_supplement": True}
    )
    source = VersionBundle("a" * 64, "b" * 64, "c" * 64, "d" * 64, {}, attached, b"", documents())
    annotations = preview(source)["annotations"]
    assert [a["target"] for a in annotations] == ["paragraph:0:0"]
    assert [event["kind"] for event in annotations[0]["values"]["events"]] == ["result_date"]
