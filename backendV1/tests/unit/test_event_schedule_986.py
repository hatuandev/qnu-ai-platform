from copy import deepcopy
from dataclasses import replace

import pytest
from pydantic import ValidationError

from qnu.domains.knowledge.compilation.source_first import build_source_draft
from qnu.domains.knowledge.compilation.supplement import confirm
from qnu.domains.knowledge.metadata import RetrievalAnnotation, validate_annotations
from qnu.domains.knowledge.publication.automatic_metadata import preview
from qnu.domains.knowledge.publication.evidence import VersionBundle


def bundle(*texts):
    blocks = [
        {"evidence_id": f"ev{i}", "text": text, "type": "paragraph"} for i, text in enumerate(texts)
    ]
    draft = {
        "sections": [
            {
                "heading": "Nội dung",
                "paragraphs": [
                    {"text": b["text"], "citations": [f"ocr:{b['evidence_id']}"]} for b in blocks
                ],
            }
        ],
        "citations": {f"ocr:{b['evidence_id']}": {"page": 1} for b in blocks},
        "source_tables": [],
    }
    return VersionBundle(
        "a" * 64,
        "b" * 64,
        "c" * 64,
        "d" * 64,
        {},
        draft,
        b"",
        [{"ocr_run_id": "ocr", "pages": [{"page_number": 1, "blocks": blocks}]}],
    )


def events_of(result):
    return [a for a in result["annotations"] if a["values"].get("events")]


def test_fees_exam_dates_and_enrollment_keep_distinct_activities_and_cutoffs():
    source = bundle(
        "Thời gian nộp lệ phí xét tuyển trực tuyến trên hệ thống là từ ngày 15/07/2026 "
        "đến 17 giờ 00 ngày 21/07/2026.",
        "Trường tổ chức thi năng khiếu dành cho hai ngành vào các ngày 19, 20 và 21/06/2026. "
        "Thí sinh đăng ký dự thi năng khiếu trên hệ thống trong khoảng từ ngày 20/05/2026 "
        "đến ngày 15/06/2026 theo thông báo.",
        "Thời gian xác nhận nhập học trực tuyến là từ ngày 13/08/2026 "
        "đến trước 17 giờ 00 ngày 21/08/2026.",
    )
    annotations = events_of(preview(source))
    validate_annotations(annotations, source.content, source.documents)
    events = {
        event["kind"]: event
        for annotation in annotations
        for event in annotation["values"]["events"]
    }
    assert set(events) == {
        "fee_deadline",
        "exam_date",
        "registration_deadline",
        "enrollment_confirmation",
    }
    assert events["fee_deadline"]["window_start"] == {"date": "2026-07-15"}
    assert events["fee_deadline"]["moment"] == {"date": "2026-07-21", "time": "17:00"}
    assert events["exam_date"]["dates"] == ["2026-06-19", "2026-06-20", "2026-06-21"]
    assert events["exam_date"]["audience"] == "hai ngành"
    assert events["registration_deadline"]["moment"] == {"date": "2026-06-15"}
    assert events["enrollment_confirmation"]["moment"] == {"date": "2026-08-21", "time": "17:00"}
    assert events["enrollment_confirmation"]["end_exclusive"] is True


def test_clock_before_range_connector_is_never_assigned_to_the_end_date():
    source = bundle("Hạn nộp lệ phí từ ngày 15/07/2026 08:00 đến ngày 21/07/2026.")
    assert events_of(preview(source)) == []


def test_source_first_preserves_evidence_for_a_schedule_cut_into_ocr_blocks():
    source = bundle(
        "Đăng ký xét tuyển: trực tuyến trên hệ",
        "thống của trường từ ngày 01/06/2025 đến",
        "ngày 30/06/2025.",
    )
    source.documents[0].update(
        evidence={f"ev{i}": {"page": 1} for i in range(3)},
        identity={},
        canonical_sha256="a" * 64,
        manifest_sha256="b" * 64,
    )
    draft = build_source_draft("Lịch đăng ký", source.documents, "compile")
    grouped = draft["sections"][0]["paragraphs"][0]
    assert grouped["citations"] == ["ocr:ev0", "ocr:ev1", "ocr:ev2"]
    assert grouped["text"].count("\n") == 2
    registered = events_of(preview(replace(source, content=draft)))
    assert len(registered) == 1
    assert registered[0]["values"]["events"][0]["moment"]["date"] == "2025-06-30"
    assert len(registered[0]["evidence"]) == 3
    source.documents[0]["pages"][0]["blocks"][1]["requires_review"] = True
    assert events_of(preview(replace(source, content=draft))) == []


def test_two_intakes_keep_their_own_deadlines():
    source = bundle("Đợt 1: hạn đăng ký ngày 30/6/2026; Đợt 2: hạn đăng ký ngày 15/7/2026")
    result = preview(source)
    found = events_of(result)
    assert len(found) == 1
    assert found[0]["target"] == "paragraph:0:0"
    assert found[0]["evidence"] == [
        {
            "citation": "ocr:ev0",
            "quote": "Đợt 1: hạn đăng ký ngày 30/6/2026",
        },
        {
            "citation": "ocr:ev0",
            "quote": "Đợt 2: hạn đăng ký ngày 15/7/2026",
        },
    ]
    assert {
        (event["intake"], event["moment"]["date"]) for event in found[0]["values"]["events"]
    } == {("Đợt 1", "2026-06-30"), ("Đợt 2", "2026-07-15")}
    assert result["conflicts"] == []


def test_exam_date_list_and_fragmented_registration_stay_separate():
    source = bundle(
        "a) Thi năng khiếu GDTC: thi vào các ngày 03,04,05/8/2026. Thí",
        "sinh đăng ký thi năng khiếu tại https://example.edu.vn từ 01/7/2026 đến",
        "27/7/2026.",
    )
    source.documents[0].update(
        evidence={f"ev{i}": {"page": 1} for i in range(3)},
        identity={},
        canonical_sha256="a" * 64,
        manifest_sha256="b" * 64,
    )
    draft = build_source_draft("Lịch thi", source.documents, "compile")
    (annotation,) = events_of(preview(replace(source, content=draft)))
    assert len(annotation["values"]["events"]) == 2
    by_kind = {event["kind"]: event for event in annotation["values"]["events"]}
    assert by_kind["exam_date"]["dates"] == ["2026-08-03", "2026-08-04", "2026-08-05"]
    assert by_kind["registration_deadline"]["window_start"] == {"date": "2026-07-01"}
    assert by_kind["registration_deadline"]["moment"] == {"date": "2026-07-27"}
    assert by_kind["registration_deadline"]["method"] == "tại https://example.edu.vn"
    assert {proof["citation"] for proof in annotation["evidence"]} == {
        "ocr:ev0",
        "ocr:ev1",
        "ocr:ev2",
    }


def test_one_intake_exam_and_result_dates_are_kept_together():
    source = bundle("Đợt 1: ngày thi 20/7/2026, công bố kết quả ngày 10/8/2026.")
    events = events_of(preview(source))[0]["values"]["events"]
    assert [(event["kind"], event["moment"]["date"]) for event in events] == [
        ("exam_date", "2026-07-20"),
        ("result_date", "2026-08-10"),
    ]
    assert {event["intake"] for event in events} == {"Đợt 1"}


def test_missing_year_keeps_partial_precision():
    events = events_of(preview(bundle("Ngày thi: 20/7")))[0]["values"]["events"]
    assert events[0]["moment"] == {"month": 7, "day": 20}
    assert "date" not in events[0]["moment"]


def test_intake_suffix_is_kept_on_its_own_event():
    result = preview(bundle("Thời gian nhận hồ sơ đợt 1: từ 10/07/2026 đến 20/07/2026"))
    annotations = events_of(result)
    assert len(annotations) == 1
    assert "attributes" not in annotations[0]["values"]
    event = annotations[0]["values"]["events"][0]
    assert event["intake"] == "đợt 1"
    assert event["window_start"] == {"date": "2026-07-10"}
    assert event["moment"] == {"date": "2026-07-20"}


def test_dates_for_same_intake_conflict_across_paragraphs():
    result = preview(
        bundle(
            "Đợt 1: công bố kết quả ngày 10/8/2026",
            "đợt 1: công bố kết quả ngày 12/8/2026",
            "Đợt 2: công bố kết quả ngày 14/8/2026",
        )
    )
    assert len(events_of(result)) == 3
    assert [conflict["intake"] for conflict in result["conflicts"]] == ["Đợt 1"]


def test_registration_channels_keep_separate_time_windows():
    result = preview(
        bundle(
            "Thí sinh đăng ký thông tin xét tuyển (học bạ, ĐGNL) trực tuyến "
            "trên cổng của trường từ ngày 01/6/2025 đến ngày 30/6/2025.",
            "Tất cả thí sinh đăng ký xét tuyển trên hệ thống của Bộ "
            "từ ngày 16/7/2025 đến ngày 28/7/2025.",
        )
    )
    assert result["conflicts"] == []
    assert {
        (event["method"], event["window_start"]["date"], event["moment"]["date"])
        for item in events_of(result)
        for event in item["values"]["events"]
    } == {
        ("trực tuyến trên cổng của trường", "2025-06-01", "2025-06-30"),
        ("trên hệ thống của Bộ", "2025-07-16", "2025-07-28"),
    }


def test_second_intake_can_continue_the_same_schedule_in_the_source_paragraph():
    text = "Thời gian nhận hồ sơ đợt 1: từ 15/6 đến 30/6. Đợt 2: từ 01/8 đến 15/8."
    result = preview(bundle(text))
    assert [
        (e["intake"], e["window_start"], e["moment"])
        for item in events_of(result)
        for e in item["values"]["events"]
    ] == [
        ("đợt 1", {"month": 6, "day": 15}, {"month": 6, "day": 30}),
        ("Đợt 2", {"month": 8, "day": 1}, {"month": 8, "day": 15}),
    ]


def test_model_cannot_pair_exam_label_with_result_date():
    text = "Lịch thi diễn ra ngày 12/07/2026. Ngày công bố kết quả là 20/07/2026."
    source = bundle(text)
    source.content["supplement"] = {
        "metadata": [
            {
                "annotation": {
                    "target": "paragraph:0:0",
                    "values": {
                        "events": [
                            {
                                "kind": "exam_date",
                                "label": "Lịch thi",
                                "moment": {"date": "2026-07-20"},
                            }
                        ]
                    },
                    "evidence": [{"citation": "ocr:ev0", "quote": text}],
                }
            }
        ]
    }
    found = events_of(preview(source))[0]["values"]["events"]
    assert {(event["kind"], event["moment"]["date"]) for event in found} == {
        ("exam_date", "2026-07-12"),
        ("result_date", "2026-07-20"),
    }


def test_calendar_window_crosses_year_boundary():
    events = events_of(
        preview(bundle("Thời gian đăng ký từ ngày 15/12/2026 đến ngày 10/01/2027."))
    )[0]["values"]["events"]
    assert events[0]["window_start"] == {"date": "2026-12-15"}
    assert events[0]["moment"] == {"date": "2027-01-10"}


def test_extended_deadline_is_kept_without_conflict():
    result = preview(
        bundle(
            "Đợt 1: hạn đăng ký ngày 30/6/2026\nĐợt 1: gia hạn thời gian đăng ký đến ngày 15/7/2026"
        )
    )
    events = events_of(result)[0]["values"]["events"]
    assert {event["moment"]["date"] for event in events} == {"2026-06-30", "2026-07-15"}
    assert [event.get("note") for event in events if event.get("note")] == ["gia hạn"]
    assert result["conflicts"] == []


def test_relative_deadline_is_stored_not_calculated():
    events = events_of(
        preview(bundle("Hạn nộp hồ sơ: trong vòng 10 ngày kể từ ngày công bố kết quả."))
    )[0]["values"]["events"]
    assert events[0]["relative"] == {
        "value": 10,
        "unit": "day",
        "from_event": "ngày công bố kết quả",
    }
    assert "moment" not in events[0] and "window_start" not in events[0]


def test_date_only_in_legal_basis_does_not_become_event():
    result = preview(
        bundle(
            "Căn cứ Quyết định số 123/QĐ-ĐH ngày 15/6/2026, "
            "Trường thông báo hạn đăng ký ngày 30/7/2026."
        )
    )
    events = events_of(result)[0]["values"]["events"]
    assert len(events) == 1
    assert events[0]["kind"] == "registration_deadline"
    assert events[0]["moment"] == {"date": "2026-07-30"}
    assert all("2026-06-15" not in str(event) for event in events)


def test_cover_letter_scene_without_schedule_labels_yields_no_events():
    result = preview(bundle("Căn cứ Quyết định số 123/QĐ-ĐH ngày 15/6/2026."))
    assert not events_of(result)


def test_competing_calendars_keep_both_and_report_conflict():
    source = bundle("Đợt 1: công bố kết quả ngày 10/8/2026\nĐợt 1: công bố kết quả ngày 12/8/2026")
    result = preview(source)
    events = events_of(result)[0]["values"]["events"]
    assert {event["moment"]["date"] for event in events} == {"2026-08-10", "2026-08-12"}
    assert result["conflicts"] == [
        {
            "target": "paragraph:0:0",
            "kind": "result_date",
            "intake": "Đợt 1",
            "audience": None,
            "method": None,
            "labels": ["công bố kết quả", "công bố kết quả"],
        }
    ]
    assert result == preview(deepcopy(source))


def test_document_target_events_are_rejected():
    with pytest.raises(ValidationError, match="Lịch và thời hạn"):
        RetrievalAnnotation.model_validate(
            {
                "target": "document",
                "values": {
                    "events": [
                        {
                            "kind": "result_date",
                            "label": "công bố kết quả",
                            "moment": {"date": "2026-08-10"},
                        }
                    ]
                },
                "evidence": [{"citation": "ocr:ev0", "quote": "công bố kết quả ngày 10/8/2026"}],
            }
        )


def test_stored_event_is_rechecked_against_its_own_evidence():
    source = bundle("Ngày công bố kết quả: 10/8/2026")
    source.content["supplement"] = {
        "metadata": [
            {
                "annotation": {
                    "target": "paragraph:0:0",
                    "values": {
                        "events": [
                            {
                                "kind": "result_date",
                                "label": "công bố kết quả",
                                "moment": {"date": "2026-08-12"},
                            }
                        ]
                    },
                    "evidence": [
                        {"citation": "ocr:ev0", "quote": "Ngày công bố kết quả: 10/8/2026"}
                    ],
                }
            }
        ]
    }
    events = events_of(preview(source))[0]["values"]["events"]
    assert [event["moment"]["date"] for event in events] == ["2026-08-10"]


def test_stored_publication_date_without_result_label_stays_unclassified():
    source = bundle("Lịch công bố: 15/6/2026")
    source.content["supplement"] = {
        "metadata": [
            {
                "annotation": {
                    "target": "paragraph:0:0",
                    "values": {
                        "events": [
                            {
                                "kind": "result_date",
                                "label": "Lịch công bố",
                                "moment": {"date": "2026-06-15"},
                            }
                        ]
                    },
                    "evidence": [{"citation": "ocr:ev0", "quote": "Lịch công bố: 15/6/2026"}],
                }
            }
        ]
    }
    assert events_of(preview(source)) == []
    # Already registered versions retain their original read contract.
    from qnu.domains.knowledge.metadata import validate_annotations

    saved = [source.content["supplement"]["metadata"][0]["annotation"]]
    validate_annotations(saved, source.content, source.documents)


def test_confirm_merges_events_for_the_same_target():
    events = [
        {
            "kind": "exam_date",
            "label": "ngày thi",
            "moment": {"date": "2026-07-20"},
        },
        {
            "kind": "result_date",
            "label": "công bố kết quả",
            "moment": {"date": "2026-08-10"},
        },
    ]
    content = {
        "supplement": {
            "metadata": [
                {
                    "id": str(index),
                    "annotation": {
                        "target": "paragraph:0:0",
                        "values": {"events": [event]},
                        "evidence": [
                            {"citation": "ocr:ev0", "quote": "Đợt 1: ngày thi và công bố"}
                        ],
                    },
                }
                for index, event in enumerate(events)
            ]
        }
    }
    merged = confirm(content, ids=["0", "1"], manual=[])
    assert [event["kind"] for event in merged[0]["values"]["events"]] == [
        "exam_date",
        "result_date",
    ]
