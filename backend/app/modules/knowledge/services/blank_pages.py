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


def _isolated_scan_noise(stats: np.ndarray, centers: np.ndarray, pixels: int, size: int) -> bool:
    """Sparse specks may be larger than one pixel; aligned glyphs/rules are not noise."""
    if pixels > min(400, size * 0.0002) or len(stats) > 80:
        return False
    if np.any(stats[:, cv2.CC_STAT_AREA] > 40) or np.any(stats[:, 2:4] > 12):
        return False
    glyphs = centers[(stats[:, cv2.CC_STAT_HEIGHT] >= 5) & (stats[:, cv2.CC_STAT_WIDTH] >= 2)]
    for center in glyphs:
        aligned = (np.abs(glyphs[:, 1] - center[1]) <= 5) & (np.abs(glyphs[:, 0] - center[0]) <= 60)
        if np.count_nonzero(aligned) >= 2:
            return False
    return True


@dataclass(frozen=True)
class BlankPageEvidence:
    is_blank: bool
    background_level: float
    foreground_pixels: int
    largest_component: int
    method: str = "raster-components-v2"

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
    _, _, stats, centers = cv2.connectedComponentsWithStats(mask, connectivity=8)
    largest = int(stats[1:, cv2.CC_STAT_AREA].max(initial=0))
    longest = int(stats[1:, cv2.CC_STAT_WIDTH:cv2.CC_STAT_HEIGHT + 1].max(initial=0))
    foreground = int(np.count_nonzero(mask))
    speck_budget = min(MAX_TOTAL_SPECK_PIXELS, image.size * MAX_SPECK_DENSITY)
    tiny_noise = foreground <= speck_budget and largest <= MAX_SPECK_AREA and longest <= MAX_SPECK_EDGE
    is_blank = background >= MIN_PAPER_LEVEL and (
        tiny_noise or _isolated_scan_noise(stats[1:], centers[1:], foreground, image.size)
    )
    return BlankPageEvidence(is_blank, background, foreground, largest)
