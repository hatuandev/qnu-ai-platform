from qnu.domains.ocr.review.defaults import SpellingDefaults, eligible_ids
from tests.integration.knowledge_support import EDITOR, PLATFORM, active_actor, as_actor


def test_spelling_defaults_are_global_and_require_system_permission(client):
    path = "/platform/v1alpha1/settings/spelling"
    value = {"ocr": False, "pdf_text": True, "word_text": True}
    previous = active_actor()
    try:
        as_actor(PLATFORM)
        assert client.get(path).json() == {"ocr": True, "pdf_text": False, "word_text": False}
        assert client.put(path, json=value).json() == value
        assert client.get(path).json() == value
        as_actor(EDITOR)
        assert client.get(path).status_code == 403
        assert client.put(path, json=value).status_code == 403
    finally:
        as_actor(previous)


def test_spelling_scope_uses_extraction_origin_including_table_cells():
    source = {
        "pages": [
            {
                "page_number": 1,
                "blocks": [
                    {
                        "evidence_id": "native",
                        "bbox": {},
                        "type": "text",
                        "text": "Gốc",
                        "origin": "native",
                    },
                    {"evidence_id": "scan", "bbox": {}, "type": "text", "text": "Ảnh"},
                    {
                        "evidence_id": "table",
                        "bbox": {},
                        "type": "table",
                        "origin": "native",
                        "table": {
                            "status": "parsed",
                            "rows": [[{"evidence_id": "cell", "text": "Nội dung"}]],
                        },
                    },
                ],
            }
        ]
    }
    assert eligible_ids(source, ".pdf", SpellingDefaults()) == {"scan"}
    assert eligible_ids(source, ".pdf", SpellingDefaults(pdf_text=True)) == {
        "scan",
        "native",
        "cell",
    }
    assert eligible_ids(source, ".docx", SpellingDefaults(pdf_text=True)) == {"scan"}
    assert eligible_ids(source, ".docx", SpellingDefaults(ocr=False, word_text=True)) == {
        "native",
        "cell",
    }
