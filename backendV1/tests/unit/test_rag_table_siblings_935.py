"""Section-sibling tables: verified heading proof, bounded, optional under budget."""

from types import SimpleNamespace

import pytest

from qnu.domains.knowledge.metadata import MetadataFilter
from qnu.domains.rag.answer.cells import catalog
from qnu.domains.rag.answer.packing import pack_messages
from qnu.domains.rag.answer.schemas import AnswerRequest
from qnu.domains.rag.answer.table_support import MAX_SECTION_SIBLINGS, section_siblings
from tests.unit.test_table_grounding_770 import source

HEADING = "run:h1"


def row(
    key,
    *,
    ordinal,
    citation,
    heading=HEADING,
    input_id="input",
    total=3,
    indices=None,
    year=None,
    kind="table",
):
    structure = {
        "source_table_citation": citation,
        "row_indices": list(range(total)) if indices is None else indices,
        "original_row_count": total,
        "context": {"source_heading_citation": heading},
    }
    if year is not None:
        structure["retrieval_metadata"] = [{"values": {"data_year": year}}]
    return SimpleNamespace(
        id=key, input_id=input_id, kind=kind, ordinal=ordinal, structure=structure
    )


def typed_link(ref):
    return {"basis": "native_typed_columns/v1", "header": ref, "chain": [ref], "previous": None}


def hit(key):
    return SimpleNamespace(chunk_id=key)


def test_complete_sibling_under_the_same_verified_heading_is_selected_with_provenance():
    anchor = row("A", ordinal=5, citation="run:t1")
    sibling = row("B", ordinal=6, citation="run:t2")
    relationships = {("input", "run:t2"): typed_link("run:t2")}
    selected, links = section_siblings(
        [hit("A")], [anchor, sibling], relationships, [MetadataFilter()], excluded=set()
    )
    assert set(selected) == {"B"}
    assert links == [
        {
            **typed_link("run:t2"),
            "chunk_id": "B",
            "support_ids": ["B"],
            "sibling_of": "A",
            "heading_citation": HEADING,
        }
    ]


@pytest.mark.parametrize(
    "change",
    ["fragment", "other_heading", "other_input", "same_table", "no_link", "foreign_header", "excluded", "narrative"],
)
def test_unproven_or_unrelated_tables_are_never_siblings(change):
    anchor = row("A", ordinal=5, citation="run:t1")
    kwargs = {}
    relationships = {("input", "run:t2"): typed_link("run:t2")}
    excluded = set()
    if change == "fragment":
        kwargs = {"indices": [0, 1]}
    elif change == "other_heading":
        kwargs = {"heading": "run:h2"}
    elif change == "other_input":
        kwargs = {"input_id": "other"}
    elif change == "same_table":
        kwargs = {"citation": "run:t1"}
    elif change == "no_link":
        relationships = {}
    elif change == "foreign_header":
        relationships = {("input", "run:t2"): {**typed_link("run:t2"), "header": "run:t0"}}
    elif change == "excluded":
        excluded = {"B"}
    else:
        kwargs = {"kind": "paragraph"}
    sibling = row("B", ordinal=6, **{"citation": "run:t2", **kwargs})
    assert section_siblings(
        [hit("A")], [anchor, sibling], relationships, [MetadataFilter()], excluded=excluded
    ) == ({}, [])


def test_sibling_must_match_a_scope_shared_with_the_anchor():
    anchor = row("A", ordinal=5, citation="run:t1", year=2031)
    sibling = row("B", ordinal=6, citation="run:t2", year=2032)
    relationships = {("input", "run:t2"): typed_link("run:t2")}
    assert section_siblings(
        [hit("A")],
        [anchor, sibling],
        relationships,
        [MetadataFilter(data_year=2031)],
        excluded=set(),
    ) == ({}, [])
    assert section_siblings(
        [hit("A")],
        [anchor, sibling],
        relationships,
        [MetadataFilter(data_year=2031), MetadataFilter(data_year=2032)],
        excluded=set(),
    ) == ({}, [])
    anchor.structure["retrieval_metadata"].append({"values": {"data_year": 2032}})
    selected, _ = section_siblings(
        [hit("A")],
        [anchor, sibling],
        relationships,
        [MetadataFilter(data_year=2031), MetadataFilter(data_year=2032)],
        excluded=set(),
    )
    assert set(selected) == {"B"}


def test_siblings_are_bounded_and_nearest_in_source_order_first():
    anchor = row("A", ordinal=10, citation="run:t1")
    near = row("B", ordinal=11, citation="run:t2")
    mid = row("C", ordinal=12, citation="run:t3")
    far = row("D", ordinal=20, citation="run:t4")
    relationships = {
        ("input", ref): typed_link(ref) for ref in ("run:t2", "run:t3", "run:t4")
    }
    selected, links = section_siblings(
        [hit("A")], [anchor, far, mid, near], relationships, [MetadataFilter()], excluded=set()
    )
    assert set(selected) == {"B", "C"}
    assert len(links) == MAX_SECTION_SIBLINGS
    second_anchor = row("E", ordinal=30, citation="run:t5")
    assert section_siblings(
        [hit("A"), hit("E")],
        [anchor, second_anchor, near, mid, far],
        relationships,
        [MetadataFilter()],
        excluded=set(),
    )[0].keys() == {"B", "C"}


def test_anchor_without_a_verified_heading_or_table_kind_selects_nothing():
    sibling = row("B", ordinal=6, citation="run:t2")
    relationships = {("input", "run:t2"): typed_link("run:t2")}
    no_heading = row("A", ordinal=5, citation="run:t1", heading=None)
    narrative = row("N", ordinal=4, citation="run:t1", kind="paragraph")
    assert section_siblings(
        [hit("A"), hit("N"), hit("missing")],
        [no_heading, narrative, sibling],
        relationships,
        [MetadataFilter()],
        excluded=set(),
    ) == ({}, [])


def test_sibling_link_makes_an_unflagged_conversion_table_selectable():
    sibling = source(
        [["Điểm VSTEP", "Điểm quy đổi"], ["4.0", "8.0"], ["5.0", "8.5"], ["6.0", "9.0"]],
        headers=0,
    )
    assert catalog([sibling])["issues"] == [
        {"evidence_id": "E1", "issues": ["header_unresolved"]}
    ]
    link = {
        **typed_link("ocr:t"),
        "chunk_id": sibling.chunk_id,
        "support_ids": [sibling.chunk_id],
        "sibling_of": "anchor",
        "heading_citation": HEADING,
    }
    cells = catalog([sibling], [link])
    assert not cells["issues"]
    assert {cell["value"] for cell in cells["tables"][0]["cells"]} == {"8.0", "8.5", "9.0"}


def test_packing_trims_a_sibling_before_failing_the_budget():
    primary = source([["Item", "Cost"], ["Motor", "12"]])
    sibling = source(
        [["Điểm VSTEP", "Điểm quy đổi"], ["4.0", "8.0"], ["5.0", "8.5"]],
        headers=0,
        key="E2",
        table="ocr:t2",
    )
    link = {
        **typed_link("ocr:t2"),
        "chunk_id": sibling.chunk_id,
        "support_ids": [sibling.chunk_id],
        "sibling_of": primary.chunk_id,
        "heading_citation": HEADING,
    }
    context = {
        "primary_ids": [primary.chunk_id],
        "table_links": [link],
        "support_ids": [sibling.chunk_id],
        "added": [
            {
                "chunk_id": sibling.chunk_id,
                "primary_chunk_id": primary.chunk_id,
                "kind": "sibling_table",
            }
        ],
    }
    question = "Điểm VSTEP 4.0 quy đổi bao nhiêu?"
    roomy = AnswerRequest(question=question, context_max_bytes=100000)
    _, _, _, full_size, skipped = pack_messages(roomy, [primary, sibling], context)
    assert skipped == []
    _, _, _, solo_size, _ = pack_messages(roomy, [primary], {})
    tight = AnswerRequest(question=question, context_max_bytes=(full_size + solo_size) // 2)
    _, _, _, size, skipped = pack_messages(tight, [primary, sibling], context)
    assert skipped == [sibling.chunk_id]
    assert size <= tight.context_max_bytes