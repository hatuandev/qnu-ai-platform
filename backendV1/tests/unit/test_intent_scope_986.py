"""Explicit intent scoping: bare catalog years, event-only intakes and row intake proof."""

from types import SimpleNamespace

import pytest

from qnu.domains.knowledge.index.query_scope import resolve
from qnu.domains.knowledge.metadata import MetadataFilter, matches_metadata
from qnu.domains.rag.answer.table_selection import requested_intakes, select_catalog
from qnu.platform.errors import AppException

CITATION = "ocr:ev-table"


def corpus(*values):
    return [
        {
            "retrieval_metadata": [
                {
                    "target": "paragraph:0:0",
                    "values": item,
                    "evidence": [{"citation": "ocr:proof", "quote": "nguồn"}],
                }
            ]
        }
        for item in values
    ]


def deadline(intake, day):
    return {
        "kind": "registration_deadline",
        "label": f"Hạn đăng ký {intake}",
        "moment": {"year": 2025, "month": 7, "day": day},
        "intake": intake,
    }


def test_bare_catalog_year_scopes_data_year_without_the_word_nam():
    units = corpus({"program": "Công nghệ thông tin", "data_year": 2025})
    _, filters, _ = resolve("Điểm chuẩn Công nghệ thông tin 2025", MetadataFilter(), units)
    assert filters == [MetadataFilter(program="Công nghệ thông tin", data_year=2025)]


@pytest.mark.parametrize("year_phrase", ["2025", "năm 2025"])
def test_year_follows_catalog_membership_instead_of_asking_role(year_phrase):
    units = corpus({"program": "Công nghệ thông tin", "data_year": 2025, "issued_year": 2026})
    _, filters, _ = resolve(
        f"Điểm chuẩn Công nghệ thông tin {year_phrase}", MetadataFilter(), units
    )
    assert filters[0].data_year == 2025 and filters[0].issued_year is None


def test_numeric_count_or_hotline_is_never_a_bare_year():
    units = corpus({"program": "Công nghệ thông tin", "data_year": 2025})
    _, counted, _ = resolve("Công nghệ thông tin có 2025 sinh viên", MetadataFilter(), units)
    assert counted[0].data_year is None
    _, hotline, _ = resolve("Gọi hotline 1800", MetadataFilter(), units)
    assert hotline[0].data_year is None


def test_bare_year_present_in_both_roles_still_requires_clarification():
    units = corpus({"data_year": 2025, "issued_year": 2025})
    with pytest.raises(AppException) as exc:
        resolve("Chỉ tiêu 2025", MetadataFilter(), units)
    assert exc.value.code == "answer_scope_clarification_required"


def test_event_only_intake_resolves_and_carries_the_scope_to_matching_units():
    units = corpus(
        {"data_year": 2025, "events": [deadline("Đợt 2", 30)]},
        {"data_year": 2025, "events": [deadline("Đợt 1", 15)]},
    )
    _, filters, _ = resolve("Hạn đăng ký đợt 2 năm 2025", MetadataFilter(), units)
    assert filters == [
        MetadataFilter(intake="Đợt 2", event_year=2025, event_kind="registration_deadline")
    ]
    assert matches_metadata(units[0], filters[0])
    assert not matches_metadata(units[1], filters[0])


def test_schedule_year_is_independent_of_statistical_year_and_bound_to_the_event():
    units = corpus(
        {"data_year": 2025},
        {
            "events": [
                deadline("Đợt 1", 15),
                {
                    "kind": "registration_deadline",
                    "intake": "Đợt 2",
                    "moment": {"date": "2026-07-30"},
                },
            ]
        },
    )
    _, filters, _ = resolve("Đợt 2 đăng ký năm 2025 tới ngày nào?", MetadataFilter(), units)
    assert filters == [
        MetadataFilter(intake="Đợt 2", event_year=2025, event_kind="registration_deadline")
    ]
    assert not any(matches_metadata(unit, filters[0]) for unit in units)


@pytest.mark.parametrize(
    ("question", "kind", "time"),
    [
        ("Hạn nộp lệ phí xét tuyển năm 2026?", "fee_deadline", {"moment": {"date": "2026-07-21"}}),
        (
            "Thời gian xác nhận nhập học năm 2026?",
            "enrollment_confirmation",
            {"moment": {"date": "2026-08-21", "time": "17:00"}, "end_exclusive": True},
        ),
        (
            "Lịch thi năng khiếu năm 2026?",
            "exam_date",
            {"dates": ["2026-06-19", "2026-06-21"]},
        ),
    ],
)
def test_expanded_event_scope_uses_the_proven_activity_and_year(question, kind, time):
    units = corpus(
        {"events": [deadline("Đợt 1", 15)]},
        {"events": [{"kind": kind, **time}]},
    )
    _, filters, _ = resolve(question, MetadataFilter(), units)
    assert filters == [MetadataFilter(event_year=2026, event_kind=kind)]
    assert [matches_metadata(unit, filters[0]) for unit in units] == [False, True]


def test_registration_requires_clarification_only_when_channel_is_unresolved():
    campus = "trực tuyến trên hệ thống của Trường https://example.test"
    ministry = "trên hệ thống của Bộ"
    units = corpus(
        {"events": [{**deadline("Đợt 1", 15), "method": campus}]},
        {"events": [{**deadline("Đợt 1", 30), "method": ministry}]},
    )
    with pytest.raises(AppException) as exc:
        resolve("Đăng ký xét tuyển năm 2025 từ ngày nào?", MetadataFilter(), units)
    assert exc.value.code == "answer_scope_clarification_required"
    _, filters, _ = resolve(
        "Đăng ký trên cổng của Trường năm 2025 từ ngày nào?", MetadataFilter(), units
    )
    assert filters[0].event_method == campus
    assert matches_metadata(units[0], filters[0])
    assert not matches_metadata(units[1], filters[0])


def test_intake_metadata_matches_unit_or_event_scope():
    structure = {
        "retrieval_metadata": [
            {
                "target": "paragraph:0:0",
                "values": {"intake": "Đợt 1", "events": [deadline("Đợt 2", 30)]},
                "evidence": [{"citation": "ocr:proof", "quote": "nguồn"}],
            }
        ]
    }
    assert matches_metadata(structure, MetadataFilter(intake="Đợt 1"))
    assert matches_metadata(structure, MetadataFilter(intake="Đợt 2"))
    assert not matches_metadata(structure, MetadataFilter(intake="Đợt 3"))


def test_event_intakes_do_not_force_clarification_when_no_intake_was_asked():
    units = corpus(
        {"events": [deadline("Đợt 1", 15)]},
        {"events": [deadline("Đợt 2", 30)]},
    )
    _, filters, _ = resolve("Hạn đăng ký là khi nào?", MetadataFilter(), units)
    assert filters == [MetadataFilter(event_kind="registration_deadline")]


def table_source(events):
    return SimpleNamespace(
        evidence_id="ich_table",
        chunk_id="ich_table",
        document_id="doc",
        version_id="v",
        publication_decision_id="published",
        structure={
            "source_table_citation": CITATION,
            "retrieval_metadata": [
                {
                    "target": f"table:{CITATION}:row:{row}",
                    "values": {"events": [event]},
                    "evidence": [{"citation": "ocr:proof", "quote": "nguồn"}],
                }
                for row, event in events.items()
            ],
        },
    )


def table_cells():
    return {
        "tables": [
            {
                "evidence_id": "ich_table",
                "cells": [
                    {"cell_id": "x:r0:k0", "subject": "A", "column": 1, "value": "15/7"},
                    {"cell_id": "x:r1:k0", "subject": "A", "column": 1, "value": "30/7"},
                    {"cell_id": "x:r2:k0", "subject": "A", "column": 1, "value": "ghi chú"},
                ],
            }
        ],
        "list_continuations": [],
    }


def test_requested_intakes_reads_flat_and_disjunctive_filters():
    assert requested_intakes({"intake": "Đợt 2"}) == {"Đợt 2"}
    assert requested_intakes({"any_of": [{"intake": "Đợt 1"}, {"intake": "Đợt 2"}]}) == {
        "Đợt 1",
        "Đợt 2",
    }
    assert requested_intakes(None) == set()


def test_table_row_event_intake_drops_other_intake_and_keeps_unknown():
    source = table_source(
        {0: deadline("Đợt 1", 15), 1: deadline("Đợt 2", 30)},
    )
    narrowed = select_catalog(table_cells(), [source], "Hạn đăng ký đợt 2", [], intakes={"Đợt 2"})
    values = {cell["value"] for table in narrowed["tables"] for cell in table["cells"]}
    assert values == {"30/7", "ghi chú"}
    assert narrowed["selection"]["requested_intakes"] == ["Đợt 2"]
