"""Empty OCR must not erase faint text, thin rules or uncertain raster pages."""

import cv2
import numpy as np
import pymupdf
import pytest

from app.modules.knowledge.services.blank_pages import inspect_empty_pdf_page


def raster_pdf(kind: str) -> bytes:
    image = np.full((1684, 1190), 255, dtype=np.uint8)
    if kind == "faint_word":
        cv2.putText(image, "Text", (100, 100), cv2.FONT_HERSHEY_SIMPLEX, 0.3, 250, 1)
    elif kind == "thin_rule":
        cv2.line(image, (100, 100), (140, 100), 250, 1)
    elif kind == "noise":
        image[::50, ::50] = 100
    elif kind == "dark":
        image[:] = 0
    elif kind == "specks":
        image[100, 100] = 100
        image[1000, 1000] = 200
    _, encoded = cv2.imencode(".png", image)
    with pymupdf.open() as document:
        page = document.new_page(width=595, height=842)
        page.insert_image(page.rect, stream=encoded.tobytes())
        return document.tobytes()


@pytest.mark.parametrize("kind", ["faint_word", "thin_rule", "noise", "dark"])
def test_uncertain_or_structured_pages_are_not_blank(kind):
    assert not inspect_empty_pdf_page(raster_pdf(kind), 1).is_blank


@pytest.mark.parametrize("kind", ["white", "specks"])
def test_clean_scan_and_isolated_noise_have_blank_evidence(kind):
    evidence = inspect_empty_pdf_page(raster_pdf(kind), 1)
    assert evidence.is_blank
    assert evidence.to_metadata()["method"] == "raster-components-v1"


def test_native_text_cannot_be_discarded_even_when_invisible():
    with pymupdf.open() as document:
        page = document.new_page()
        page.insert_text((50, 50), "White hidden text", color=(1, 1, 1))
        content = document.tobytes()
    assert not inspect_empty_pdf_page(content, 1).is_blank


def test_oversized_page_is_not_classified_after_downsampling():
    with pymupdf.open() as document:
        document.new_page(width=5000, height=5000)
        content = document.tobytes()
    assert not inspect_empty_pdf_page(content, 1).is_blank
