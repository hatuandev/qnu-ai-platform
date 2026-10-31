import json
from types import SimpleNamespace

import pytest

from qnu.domains.knowledge.compilation import segments as split
from qnu.domains.knowledge.compilation.refinement import diagnose, partition, total_usage
from qnu.platform.errors import AppException
from tests.unit.test_compiler_projection_746 import cell, document, table_block, text_block


def test_only_measured_length_stop_can_refine_even_before_content():
    def raw(finish, content):
        return json.dumps(
            {"choices": [{"finish_reason": finish, "message": {"content": content}}]}
        ).encode()

    assert diagnose(raw("length", "{partial"))
    assert not diagnose(raw("stop", "content"))
    assert diagnose(raw("length", ""))
    assert not diagnose(b"422 invalid schema")


def test_usage_counts_requests_once_and_preserves_unknown():
    parent = SimpleNamespace(
        config={"refined_usage_tokens": 50}, usage_tokens=250, request_started_at=True
    )
    child = SimpleNamespace(config={}, usage_tokens=200, request_started_at=True)
    pending = SimpleNamespace(config={}, usage_tokens=None, request_started_at=None)
    assert total_usage([parent, child, pending]) == 250
    child.usage_tokens = None
    assert total_usage([parent, child]) is None
    assert total_usage([pending]) is None


def test_partition_keeps_exact_ownership_and_rowspans():
    rows = [[cell("head", "H", header=True)], [cell("a", "A")], [cell("b", "B")], [cell("c", "C")]]
    rows[1][0]["row_span"] = 2
    docs = [document([[table_block("table", rows)]])]
    refs = split.owned_refs(split.build_units(docs))
    groups = partition(docs, {"owned": refs})
    assert [[u.row_index for u in group] for group in groups] == [[1, 2], [3]]


def test_atomic_unit_is_never_cropped():
    docs = [document([[text_block("block", "Nội dung.")]])]
    with pytest.raises(AppException) as caught:
        partition(docs, {"owned": split.owned_refs(split.build_units(docs))})
    assert caught.value.code == "compilation_refinement_atomic_limit"
