from qnu.domains.knowledge.compilation.supplement import _rules
from qnu.domains.knowledge.metadata import MetadataValues, attribute_in_quote, chunk_metadata


def test_dates_require_their_own_source_labels():
    text = (
        "Hà Nội, ngày 05 tháng 11 năm 2026\n"
        "Năm dữ liệu: 2025. Văn bản có hiệu lực từ ngày 07/11/2026."
    )
    fields = {item.field: (item.value, item.scope) for item in _rules("ocr:ev", text, True)}
    assert fields == {
        "issued_year": (2026, "document"),
        "data_year": (2025, "local"),
        "effective_from": ("2026-11-07", "document"),
    }
    deadline = "Thời hạn nộp hồ sơ là ngày 05 tháng 11 năm 2026."
    assert _rules("ocr:ev", deadline, True) == []
    assert _rules("ocr:ev", "Ngày ban hành: 01/02/2024", True)[0].value == 2024
    assert _rules("ocr:ev", "Văn bản hết hiệu lực từ ngày 05/11/2026.", True) == []
    end = _rules("ocr:ev", "Văn bản có hiệu lực đến hết ngày 05/11/2026.", True)
    assert [(item.field, item.value) for item in end] == [("effective_until", "2026-11-05")]


def test_custom_values_are_typed_and_cannot_match_part_of_a_number():
    data = MetadataValues(attributes={"Mã": "0012", "Số lượng": 12, "Bật": True})
    assert data.model_dump(exclude_none=True)["attributes"] == {
        "Mã": "0012",
        "Số lượng": 12,
        "Bật": True,
    }
    assert not attribute_in_quote("Số lượng", 12, "Số lượng: 120")
    assert not attribute_in_quote("Số lượng", 12, "Số lượng: 12.5")
    assert attribute_in_quote("Số lượng", 12, "Số lượng: 12.")
    assert attribute_in_quote("Mã", "0012", "Mã: 0012")
    annotations = [
        {"target": "document", "values": {"attributes": {"a": 1}}, "evidence": []},
        {"target": "section:ocr:ev", "values": {"attributes": {"b": "2"}}, "evidence": []},
    ]
    assert chunk_metadata(annotations, {"section:ocr:ev"})[0]["values"] == {
        "attributes": {"a": 1, "b": "2"},
    }
