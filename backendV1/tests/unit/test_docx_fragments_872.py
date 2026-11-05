"""Page-table recovery needs complete, unique, literal source-cell proof."""

from copy import deepcopy
from dataclasses import replace

import pytest

from qnu.domains.ocr.artifacts.canonical import _table_payload
from qnu.domains.ocr.layout import Block, Cell, PageLayout, Table
from qnu.domains.ocr.native import NativePage, page_from_payload, page_payload
from qnu.domains.ocr.native_docx import restore_source_tables
from qnu.domains.ocr.native_docx_fragments import match_fragments


def table(rows, *, header=False):
    return Table(
        "parsed",
        tuple(
            tuple(Cell(text, header=header and i == 0) for text in row)
            for i, row in enumerate(rows)
        ),
        2,
    )


def material():
    source = table(
        [("Code", "Details"), ("0012", "First half; second half."), ("0013", "0 -")], header=True
    )
    first = table([("Code", "Details"), ("0012", "First half;")])
    second = table([("Code", "Details"), ("", "second half."), ("0013", "0 -")])
    return source, [(0, 0, first), (1, 0, second)]


def test_page_split_keeps_literal_cells_and_links_back_to_one_source_row():
    source, entries = material()
    before = deepcopy(entries)
    mapped = match_fragments([source], entries)
    assert len(mapped) == 2
    first, second = mapped[0, 0], mapped[1, 0]
    assert [[c.text for c in r] for r in second.rows] == [
        [c.text for c in r] for r in entries[1][2].rows
    ]
    assert all(c.header for c in first.rows[0]) and all(c.header for c in second.rows[0])
    assert not any(c.header for c in second.rows[1])
    link = second.source_mapping
    assert link["repeated_header"] and link["fragment_count"] == 2
    assert link["cells"][1][1]["row_index"] == 1
    assert link["cells"][1][1]["continued"]
    assert link["cells"][1][1]["text_start"] == len("Firsthalf;")
    assert link["cells"][2][0]["row_index"] == 2
    assert entries == before


@pytest.mark.parametrize(
    "case",
    ["value", "missing", "ambiguous", "page_gap", "order", "column", "vertical", "partial_inside"],
)
def test_unproven_fragments_are_not_attached(case):
    source, entries = material()
    sources = [source]
    if case == "value":
        entries[1] = (1, 0, table([("Code", "Details"), ("", "second half."), ("0013", "1 -")]))
    elif case == "missing":
        entries.pop()
    elif case == "ambiguous":
        sources.append(source)
    elif case == "page_gap":
        entries[1] = (2, 0, entries[1][2])
    elif case == "order":
        entries = [(0, 0, entries[1][2]), (1, 0, entries[0][2])]
    elif case == "column":
        entries[1] = (1, 0, table([("Details", "Code"), ("second half.", ""), ("0 -", "0013")]))
    elif case == "vertical":
        sources = [
            replace(
                source,
                rows=(
                    (replace(source.rows[0][0], row_span=2), source.rows[0][1]),
                    *source.rows[1:],
                ),
            )
        ]
    else:
        entries[0] = (0, 0, table([("Code", "Details"), ("0012", "First half;"), ("0013", "0 -")]))
    assert match_fragments(sources, entries) == {}


def test_continuation_without_repeated_header_is_supported():
    source, entries = material()
    entries[1] = (1, 0, replace(entries[1][2], rows=entries[1][2].rows[1:]))
    result = match_fragments([source], entries)
    assert len(result) == 2
    assert not result[1, 0].source_mapping["repeated_header"]
    assert not any(c.header for c in result[1, 0].rows[0])


def test_complete_independent_table_cannot_be_swallowed_as_a_page_fragment():
    source, entries = material()
    # A different source table already explains the first rendered table in full.
    # A larger table with the same literal prefix is not proof of continuity.
    separate = entries[0][2]
    assert match_fragments([source, separate], entries) == {}


def test_source_colspan_group_is_preserved():
    source, entries = material()
    group = (Cell("Shared group", col_span=2),)
    source = replace(source, rows=(source.rows[0], group, *source.rows[1:]))
    entries[0] = (
        0,
        0,
        replace(entries[0][2], rows=(entries[0][2].rows[0], group, *entries[0][2].rows[1:])),
    )
    mapped = match_fragments([source], entries)
    assert mapped[0, 0].rows[1] == group
    assert mapped[1, 0].source_mapping["cells"][1][1]["row_index"] == 2


def test_restoration_and_canonical_checkpoint_keep_fragment_provenance(monkeypatch):
    source, entries = material()
    pages = tuple(
        NativePage(
            i + 1,
            PageLayout(
                (Block(1, "Table", "table", "measured", (0, 0, 1, 1), False, t, origin="native"),)
            ),
            (),
            False,
            True,
        )
        for i, _, t in entries
    )
    monkeypatch.setattr("qnu.domains.ocr.native_docx._docling_tables", lambda _: [source])
    restored = restore_source_tables(b"unchanged", pages, converter="gotenberg-libreoffice")
    assert all(not p.layout.warnings and not p.layout.blocks[0].requires_review for p in restored)
    assert all(p.layout.blocks[0].text == "measured" for p in restored)
    second = restored[1]
    assert page_from_payload(page_payload(second, "render_pdf")).layout == second.layout
    payload = _table_payload(second.layout.blocks[0].table, 2, 1)
    assert payload["source_mapping"]["fragment_count"] == 2
    assert payload["rows"][1][0]["text"] == ""
    assert payload["rows"][1][1]["evidence_id"] == "ev_p002_b001_c01_01"


def test_unresolved_mapping_keeps_warning_and_original_geometry(monkeypatch):
    source, entries = material()
    page = NativePage(
        1,
        PageLayout(
            (Block(1, "Table", "table", "measured", (0.1, 0.2, 0.8, 0.9), False, entries[0][2]),)
        ),
        (),
        False,
        True,
    )
    monkeypatch.setattr("qnu.domains.ocr.native_docx._docling_tables", lambda _: [source])
    [result] = restore_source_tables(b"unchanged", (page,), converter="gotenberg-libreoffice")
    assert result.layout.blocks[0].bbox == page.layout.blocks[0].bbox
    assert result.layout.blocks[0].requires_review
    assert result.layout.warnings == ("docx_table_source_mapping_requires_review",)
