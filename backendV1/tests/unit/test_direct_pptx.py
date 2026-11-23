from io import BytesIO

import pytest
from PIL import Image
from pptx import Presentation
from pptx.util import Inches

from qnu.domains.knowledge.artifacts.files import detect_stored_file
from qnu.domains.knowledge.source_sections import source_sections
from qnu.domains.ocr.artifacts.canonical import PageDocument, build_canonical
from qnu.domains.ocr.artifacts.validate import validate_document
from qnu.domains.ocr.direct_pptx import extract_pptx
from qnu.platform.errors import AppException


@pytest.fixture
def presentation():
    deck = Presentation()
    first = deck.slides.add_slide(deck.slide_layouts[5])
    first.shapes.title.text = "Quy định hồ sơ"
    table = first.shapes.add_table(3, 2, 0, Inches(1), Inches(5), Inches(2)).table
    table.first_row = True
    table.cell(0, 0).text = "Nhóm"
    table.cell(0, 1).text = "Lệ phí"
    table.cell(1, 0).merge(table.cell(2, 0))
    table.cell(1, 0).text = "Nhóm A"
    table.cell(1, 1).text = "0"
    table.cell(2, 1).text = "-"
    first.notes_slide.notes_text_frame.text = "Ghi chú đối chiếu."
    second = deck.slides.add_slide(deck.slide_layouts[6])
    group = second.shapes.add_group_shape()
    group.shapes.add_textbox(0, 0, Inches(5), Inches(1)).text = "Đoạn độc lập."
    payload = BytesIO()
    deck.save(payload)
    return payload.getvalue()


def test_powerpoint_validates_and_keeps_slide_table_and_note_provenance(presentation):
    stored = detect_stored_file("tai-lieu.pptx", presentation, len(presentation))
    assert stored.extension == ".pptx"
    rendered, plan = extract_pptx(presentation, max_pages=2)
    canonical = build_canonical(
        identity={"ocr_run_id": "run"},
        processing={"renderer": rendered.renderer},
        rendered=rendered,
        pages=[
            PageDocument(p.page_number, "completed", None, None, None, None, p.layout)
            for p in plan.pages
        ],
        limits={},
    )
    assert validate_document(canonical, expected_pages=2).ok
    first, second = canonical["pages"]
    title, table, notes = first["blocks"]
    assert title["source_locator"]["level"] == 1
    assert table["source_locator"]["slide"] == 1
    assert table["table"]["rows"][1][0]["row_span"] == 2
    assert table["table"]["rows"][1][1]["text"] == "0"
    assert table["table"]["rows"][2][0]["text"] == "-"
    assert notes["text"] == "Ghi chú đối chiếu."
    assert notes["source_locator"]["part"] == "notes"
    outline = source_sections([{**canonical, "ocr_run_id": "run"}])
    assert outline[f"run:{notes['evidence_id']}"].heading == "Quy định hồ sơ"
    para = outline[f"run:{second['blocks'][0]['evidence_id']}"]
    assert para.context() == {"source_scope": {"kind": "slide", "number": 2}}
    title["source_locator"]["slide"] = 2
    assert not validate_document(canonical, expected_pages=2).ok


def test_powerpoint_rejects_bad_zip_and_slide_limit(presentation):
    with pytest.raises(AppException) as error:
        detect_stored_file("source.docx", presentation, len(presentation))
    assert error.value.code == "file_signature_mismatch"
    with pytest.raises(AppException) as error:
        extract_pptx(b"not a presentation", max_pages=2)
    assert error.value.code == "pptx_invalid"
    with pytest.raises(AppException) as error:
        extract_pptx(presentation, max_pages=1)
    assert error.value.code == "pptx_too_many_slides"


def test_powerpoint_reports_unread_graphics_without_inventing_text():
    deck = Presentation()
    slide = deck.slides.add_slide(deck.slide_layouts[6])
    image = BytesIO()
    Image.new("RGB", (4, 4)).save(image, format="PNG")
    slide.shapes.add_picture(BytesIO(image.getvalue()), 0, 0)
    payload = BytesIO()
    deck.save(payload)
    with pytest.raises(AppException) as error:
        extract_pptx(payload.getvalue(), max_pages=1)
    assert error.value.code == "pptx_slide_requires_review"

    slide.shapes.add_textbox(0, 0, Inches(5), Inches(1)).text = "Văn bản nguồn"
    payload = BytesIO()
    deck.save(payload)
    _, plan = extract_pptx(payload.getvalue(), max_pages=1)
    layout = plan.pages[0].layout
    assert layout.text == "Văn bản nguồn"
    assert layout.warnings == ("pptx_graphic_requires_review",)
    assert layout.blocks[0].requires_review
