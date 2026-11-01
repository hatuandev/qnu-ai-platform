"""Literal table serialization from scan OCR; no vocabulary or source-specific fixes."""

import pytest

from qnu.domains.ocr.layout import parse_page, parse_table
from qnu.platform.errors import AppException


def test_legacy_runs_keep_the_old_parser():
    raw = r"\begin{tabular}{cc}A&B&C\\1&&3\\\end{tabular}"
    assert parse_table(raw, table_layout_version="nemotron-tabular/v1").status == "unsupported"
    with pytest.raises(AppException, match="Phiên bản parser"):
        parse_page("", table_layout_version="future")


def test_extra_empty_cells_without_a_vertical_merge_are_not_dropped():
    table = parse_table(r"\begin{tabular}{cc}&A&B\\1&2\\\end{tabular}")
    assert table.status == "unsupported"


def test_mbox_cells_preserve_empty_text_and_escaped_characters():
    table = parse_table(r"\begin{tabular}{cc}2. & \mbox{}\\\mbox{A\&B} & \text{C}\\\end{tabular}")
    assert table.status == "parsed"
    assert [[c.text for c in row] for row in table.rows] == [["2.", ""], ["A&B", "C"]]


def test_consistent_literal_rows_reconcile_only_the_wrong_column_spec():
    raw = r"\begin{tabular}{cc}A&B&C\\1&&3\\\end{tabular}"
    table = parse_table(raw)
    assert table.status == "parsed" and table.column_count == 3
    assert table.reason == "column_spec_reconciled"
    assert [[c.text for c in row] for row in table.rows] == [["A", "B", "C"], ["1", "", "3"]]
    layout = parse_page(f"<x_0.1><y_0.1>{raw}<x_0.9><y_0.9><class_Table>")
    assert layout.blocks[0].requires_review
    assert "table_reconciled:column_spec_reconciled" in layout.warnings


def test_conflicting_row_widths_are_not_guessed_or_padded():
    table = parse_table(r"\begin{tabular}{cc}2.&\mbox{}&\mbox{}\\3.&\mbox{}\\\end{tabular}")
    assert table.status == "unsupported" and table.reason == "grid_mismatch"


def test_unknown_commands_are_still_unsupported():
    table = parse_table(r"\begin{tabular}{cc}A&\input{other}\\\end{tabular}")
    assert table.status == "unsupported"
