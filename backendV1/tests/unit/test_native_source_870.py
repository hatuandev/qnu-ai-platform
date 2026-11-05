"""Measured source glyphs restore cell order without guessing identifiers or values."""

import pymupdf
import pytest

from qnu.domains.ocr.image_regions import image_pdf
from qnu.domains.ocr.layout import Block, PageLayout
from qnu.domains.ocr.mineru_layout import VERSION, parse_mineru_page
from qnu.domains.ocr.native import NativePage, merge_layout
from qnu.domains.ocr.native_tables import table_regions
from qnu.platform.errors import AppException


def identifier_pdf():
    document = pymupdf.open()
    page = document.new_page()
    for x in (40, 190, 330):
        page.draw_line((x, 60), (x, 120))
    for y in (60, 90, 120):
        page.draw_line((40, y), (330, y))
    for x, y, value in [
        (45, 80, "Field"),
        (195, 80, "Value"),
        (45, 110, "field_code_01"),
        (195, 110, "0012"),
    ]:
        page.insert_text((x, y), value, fontname="tiro", fontsize=9)
    return document


def test_cell_glyph_order_preserves_underscores_and_literal_numbers():
    with identifier_pdf() as document:
        [(_, table)] = table_regions(document[0])
    assert table.rows[1][0].text == "field_code_01"
    assert table.rows[1][1].text == "0012"


def test_geometry_cannot_silently_add_or_drop_a_cell_character(monkeypatch):
    original = pymupdf.Page.get_text

    def changed(page, option="text", *args, **kwargs):
        if option == "text" and kwargs.get("clip"):
            return "changed identifier"
        return original(page, option, *args, **kwargs)

    monkeypatch.setattr(pymupdf.Page, "get_text", changed)
    with identifier_pdf() as document:
        [(_, table)] = table_regions(document[0])
    assert "changed" not in str(table.rows)
    assert table.rows[1][1].text == "0012"


def image_result(text="NODE A"):
    return {
        "format": VERSION,
        "page": {"blocks": [{"type": "text", "bbox": [0.1, 0.2, 0.9, 0.8], "content": text}]},
    }


def region_raw(text="NODE A"):
    return {
        "format": VERSION,
        "page": {"blocks": []},
        "image_ocr": [
            {"image_asset_no": 10001, "bbox": [0.2, 0.3, 0.8, 0.6], "result": image_result(text)}
        ],
    }


def test_image_only_pdf_is_deterministic_for_resume():
    pixmap = pymupdf.Pixmap(pymupdf.csRGB, pymupdf.IRect(0, 0, 100, 40), False)
    pixmap.clear_with(200)
    image = pixmap.tobytes("png")
    assert image_pdf(image) == image_pdf(image)
    pdf, regions = image_pdf(image)
    assert regions == [(0, 0, 1, 1)]
    with pymupdf.open(stream=pdf, filetype="pdf") as document:
        assert len(document) == 1
        assert document[0].get_text() == ""
        assert len(document[0].get_images()) == 1


def panel_picture():
    with pymupdf.open() as document:
        page = document.new_page(width=600, height=180)
        for left, label in [(20, "FIRST PANEL"), (320, "SECOND PANEL")]:
            page.draw_rect(pymupdf.Rect(left, 20, left + 220, 130), width=2)
            page.insert_text((left + 25, 55), label, fontsize=16)
            page.insert_text((left + 25, 90), "Literal 0012 - 0", fontsize=12)
        return page.get_pixmap(matrix=pymupdf.Matrix(2, 2)).tobytes("png")


def test_closed_panels_keep_original_picture_and_crop_all_internal_labels():
    picture = panel_picture()
    pdf, regions = image_pdf(picture)
    assert len(regions) == 3
    assert image_pdf(picture) == (pdf, regions)
    assert regions[1][2] < regions[2][0]
    with pymupdf.open(stream=pdf, filetype="pdf") as document:
        assert len(document) == 3
        assert all(not page.get_text() and page.get_images() for page in document)


def test_separate_panels_of_one_asset_preserve_mapping():
    raw = region_raw()
    raw["image_ocr"].append(
        {**raw["image_ocr"][0], "image_region": 2, "bbox": [0.3, 0.3, 0.4, 0.4]}
    )
    layout = parse_mineru_page(raw)
    assert len(layout.blocks) == 2
    assert layout.blocks[1].bbox == pytest.approx((0.31, 0.32, 0.39, 0.38))


def test_crop_text_is_projected_to_source_and_does_not_replace_native_text():
    layout = parse_mineru_page(region_raw())
    [crop] = layout.blocks
    assert crop.bbox == pytest.approx((0.26, 0.36, 0.74, 0.54))
    assert crop.source_image_asset_no == 10001 and crop.requires_review
    native = NativePage(
        1,
        PageLayout(
            (
                Block(1, "Text", "text", "Original body", (0.1, 0.1, 0.9, 0.2), False),
                Block(
                    2,
                    "Picture",
                    "figure",
                    "",
                    (0.2, 0.3, 0.8, 0.6),
                    True,
                    image={"asset_no": 10001},
                ),
            )
        ),
        (),
        True,
        True,
    )
    duplicate = Block(3, "Text", "text", "NODE A", crop.bbox, False)
    merged = merge_layout(native, PageLayout((duplicate, crop)))
    assert merged.text.count("NODE A") == 1
    assert "Original body" in merged.text
    assert next(b for b in merged.blocks if b.text == "NODE A").source_image_asset_no == 10001


def test_empty_crop_keeps_an_explicit_unresolved_warning():
    layout = parse_mineru_page(region_raw(""))
    assert layout.warnings == ("image_text_unresolved:10001",)


@pytest.mark.parametrize("case", ["bbox", "duplicate", "nested", "result"])
def test_image_projection_rejects_invalid_or_unbounded_provenance(case):
    raw = region_raw()
    region = raw["image_ocr"][0]
    if case == "bbox":
        region["bbox"] = [0.5, 0.5, 0.4, 0.4]
    elif case == "duplicate":
        raw["image_ocr"].append(region)
    elif case == "nested":
        region["result"]["image_ocr"] = [region]
    else:
        region["result"] = []
    with pytest.raises(AppException) as caught:
        parse_mineru_page(raw)
    assert caught.value.code == "mineru_layout_invalid"
