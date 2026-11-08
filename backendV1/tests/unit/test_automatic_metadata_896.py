from copy import deepcopy
from dataclasses import replace

import pytest

from qnu.domains.knowledge.compilation.supplement import MetadataCandidate, _proposal_values
from qnu.domains.knowledge.metadata import MetadataFilter, chunk_metadata, matches_metadata
from qnu.domains.knowledge.publication.automatic_metadata import preview
from qnu.domains.knowledge.publication.evidence import VersionBundle
from qnu.domains.knowledge.publication.schemas import RegisterVersionRequest
from qnu.domains.knowledge.publication.service import _request_payload


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


@pytest.mark.parametrize(
    "field,value,quote",
    [
        ("program", "Tuyển sinh 2026", "mùa Tuyển sinh 2026"),
        ("intake", "2026", "tuyển sinh 2026"),
        ("issued_year", 2026, "Năm dữ liệu: 2026"),
        ("data_year", 2026, "Ngày ban hành: 01/02/2026"),
        ("data_year", 2026, "Năm dữ liệu: 2026 - 2027"),
        ("data_year", 2026, "Năm dữ liệu: 2026 và 2027"),
    ],
)
def test_literal_occurrence_alone_does_not_prove_role(field, value, quote):
    assert not _proposal_values(
        MetadataCandidate(field=field, value=value, quote=quote, citation="ocr:ev"), True
    )


def test_auto_correct_roles_and_dynamic_attributes_without_mutating_source():
    source = bundle(
        "Mùa tuyển sinh 2026",
        "Ngày ban hành: 01/02/2025",
        "Ngành: Công nghệ sinh học\nĐợt: Đợt 2\nMã đơn vị: 0012",
    )
    before = deepcopy(source)
    result = preview(source)
    annotations = {a["target"]: a for a in result["annotations"]}
    assert annotations["paragraph:0:0"]["values"] == {"data_year": 2026}
    assert annotations["document"]["values"] == {"issued_year": 2025}
    assert annotations["paragraph:0:2"]["values"] == {
        "program": "Công nghệ sinh học",
        "intake": "Đợt 2",
        "attributes": {"Mã đơn vị": "0012"},
    }
    assert source == before
    assert result == preview(source)
    assert preview(replace(source, bundle_sha256="e" * 64))["sha256"] != result["sha256"]
    # A local year does not turn every paragraph into the same year's content.
    other = {"retrieval_metadata": chunk_metadata(result["annotations"], {"paragraph:0:2"})}
    assert not matches_metadata(other, MetadataFilter(data_year=2026))


def test_old_misclassified_ai_proposals_are_rechecked_and_unverified_pairs_not_imported():
    source = bundle("Mùa tuyển sinh 2026", "Trường có Mã 0012. Phần khác có số 9999.")
    source.content["supplement"] = {
        "metadata": [
            {
                "annotation": {
                    "target": "paragraph:0:0",
                    "values": {"program": "tuyển sinh 2026", "intake": "2026"},
                    "evidence": [{"citation": "ocr:ev0", "quote": "tuyển sinh 2026"}],
                }
            },
            {
                "annotation": {
                    "target": "paragraph:0:1",
                    "values": {"attributes": {"Mã": "9999"}},
                    "evidence": [
                        {"citation": "ocr:ev1", "quote": "Trường có Mã 0012. Phần khác có số 9999."}
                    ],
                }
            },
        ]
    }
    values = [a["values"] for a in preview(source)["annotations"]]
    assert values == [{"data_year": 2026}]


def test_conflicting_values_remain_unknown_but_unrelated_values_survive():
    source = bundle(
        "Năm dữ liệu: 2025\nNăm dữ liệu: 2026\nMã đơn vị: 0012",
        "Ngày ban hành: 01/02/2024",
        "Ngày ban hành: 03/04/2025",
    )
    annotations = preview(source)["annotations"]
    assert annotations == [
        {
            "target": "paragraph:0:0",
            "values": {"attributes": {"Mã đơn vị": "0012"}},
            "evidence": [{"citation": "ocr:ev0", "quote": "Mã đơn vị: 0012"}],
        }
    ]


def test_empty_and_multiple_sources_do_not_invent_global_scope():
    assert preview(bundle("Hướng dẫn chung không ghi năm hoặc ngành."))["annotations"] == []
    source = bundle("Năm dữ liệu: 2026")
    second = bundle("Năm dữ liệu: 2025").documents[0]
    second["ocr_run_id"] = "other"
    source.documents.append(second)
    # The additional source has no citation/target in this draft.
    assert [a["values"] for a in preview(source)["annotations"]] == [{"data_year": 2026}]


def test_legacy_registration_request_hash_is_unchanged():
    assert _request_payload(RegisterVersionRequest(compilation_run_id="cmp")) == {
        "compilation_run_id": "cmp"
    }
