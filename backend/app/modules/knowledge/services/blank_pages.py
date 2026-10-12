"""Conservative raster evidence for empty OCR pages, never a text fallback."""

from dataclasses import asdict, dataclass

import cv2
import numpy as np
import pymupdf

# At up to 144 DPI only isolated sub-glyph specks may be ignored. Uncertain,
# dark, noisy or faint structured pages remain nonblank and require OCR/review.
MAX_RENDER_EDGE = 2400
MIN_PAPER_LEVEL = 245
MIN_INK_CONTRAST = 3
MAX_SPECK_AREA = 16
MAX_SPECK_EDGE = 5
MAX_TOTAL_SPECK_PIXELS = 128
MAX_SPECK_DENSITY = 0.00006


@dataclass(frozen=True)
class BlankPageEvidence:
    is_blank: bool
    background_level: float
    foreground_pixels: int
    largest_component: int
    method: str = "raster-components-v1"

    def to_metadata(self) -> dict[str, bool | float | int | str]:
        return asdict(self)


def inspect_empty_pdf_page(content: bytes, page_number: int) -> BlankPageEvidence:
    """Inspect the original rendered page, not OCR output or page position."""
    with pymupdf.open(stream=content, filetype="pdf") as document:
        page = document[page_number - 1]
        if page.get_text().strip():
            return BlankPageEvidence(False, 0, 0, 0)
        scale = min(2, MAX_RENDER_EDGE / max(page.rect.width, page.rect.height))
        if scale < 1:
            # Do not classify oversized pages after shrinking possible glyphs.
            return BlankPageEvidence(False, 0, 0, 0)
        pixmap = page.get_pixmap(matrix=pymupdf.Matrix(scale, scale),
                                 colorspace=pymupdf.csGRAY, alpha=False)
        image = np.frombuffer(pixmap.samples, dtype=np.uint8).reshape(pixmap.height, pixmap.width)
    background = float(np.percentile(image, 95))
    # Both local background and global paper level are used: gradients/noise
    # conservatively block blank classification rather than erase weak ink.
    local_background = cv2.GaussianBlur(image.astype(np.float32), (0, 0), 5)
    mask = ((image < background - MIN_INK_CONTRAST)
            | (image < local_background - MIN_INK_CONTRAST)).astype(np.uint8)
    _, _, stats, _ = cv2.connectedComponentsWithStats(mask, connectivity=8)
    largest = int(stats[1:, cv2.CC_STAT_AREA].max(initial=0))
    longest = int(stats[1:, cv2.CC_STAT_WIDTH:cv2.CC_STAT_HEIGHT + 1].max(initial=0))
    foreground = int(np.count_nonzero(mask))
    speck_budget = min(MAX_TOTAL_SPECK_PIXELS, image.size * MAX_SPECK_DENSITY)
    is_blank = (background >= MIN_PAPER_LEVEL and foreground <= speck_budget
                and largest <= MAX_SPECK_AREA and longest <= MAX_SPECK_EDGE)
    return BlankPageEvidence(is_blank, background, foreground, largest)
