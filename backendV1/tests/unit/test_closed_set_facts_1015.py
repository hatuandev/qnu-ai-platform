"""Unit tests for closed-set facts computed from packed table fragments."""

from qnu.domains.rag.answer.closed_set import computed_facts
from tests.unit.test_table_grounding_770 import source


def test_no_tables_returns_none():
    computed, summary = computed_facts("Ngành nào xét Toán, Văn, Địa?", [])
    assert computed is None
    assert summary["status"] == "no_tables"
    assert summary["tables"] == 0


def test_enumeration_facts_computed_from_unselectable_table():
    hit = source(
        [
            ["Mã ngành", "Tên ngành", "Tổ hợp xét tuyển"],
            ["7140209", "Sư phạm Toán học", "(Toán, Lý, Hóa); (Toán, Hóa, Sinh)"],
            ["7140217", "Sư phạm Ngữ văn", "(Văn, Sử, Địa); (Toán, Văn, Địa)"],
            ["7140249", "Sư phạm Lịch sử - Địa lý", "(Toán, Văn, Sử); (Toán, Văn, Địa)"],
        ],
        key="E1",
        headers=1,
    )

    computed, summary = computed_facts(
        "Ngành nào xét tuyển tổ hợp Toán, Văn, Địa?",
        [hit],
        enumeration_requested=True,
    )

    assert computed is not None
    assert summary["status"] == "computed"
    assert summary["tables"] == 1
    assert "list_enumeration" in computed
    enumerations = computed["list_enumeration"]
    assert len(enumerations) == 1
    enum_fact = enumerations[0]
    matches = {m["name"]: m["evidence_ids"] for m in enum_fact["matches"]}
    assert "Sư phạm Ngữ văn" in matches
    assert "Sư phạm Lịch sử - Địa lý" in matches
    assert "Sư phạm Toán học" not in matches
    assert matches["Sư phạm Ngữ văn"] == ["E1"]


def test_membership_negative_fact_for_unoffered_combination():
    hit = source(
        [
            ["Mã ngành", "Tên ngành", "Tổ hợp xét tuyển"],
            ["7140209", "Sư phạm Toán học", "(Toán, Lý, Hóa); (Toán, Hóa, Sinh)"],
            ["7140217", "Sư phạm Ngữ văn", "(Văn, Sử, Địa); (Toán, Văn, Địa)"],
        ],
        key="E2",
        headers=1,
    )

    computed, summary = computed_facts(
        "Ngành Sư phạm Toán học có xét tổ hợp Văn, Sử, Địa?",
        [hit],
        enumeration_requested=False,
    )

    assert computed is not None
    assert summary["status"] == "computed"
    assert summary["memberships"] == 1
    assert "list_membership" in computed
    memberships = computed["list_membership"]
    assert len(memberships) == 1
    mem_fact = memberships[0]
    assert mem_fact["subject"] == "Sư phạm Toán học"
    assert mem_fact["present"] is False
    assert mem_fact["evidence_ids"] == ["E2"]


def test_selectable_tables_are_excluded():
    hit = source(
        [
            ["Tên ngành", "Tổ hợp"],
            ["Ngôn ngữ Anh", "(Toán, Văn, Anh)"],
        ],
        key="E3",
        headers=1,
    )

    computed, summary = computed_facts(
        "Ngành nào xét Toán, Văn, Anh?",
        [hit],
        enumeration_requested=True,
        exclude_evidence_ids={"E3"},
    )

    assert computed is None
    assert summary["status"] == "no_tables"
    assert summary["skipped_selectable"] == 1
