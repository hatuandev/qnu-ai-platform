"""Geometric image coverage independent of filenames, captions and vocabulary."""

import numpy as np
import pymupdf


def visual_coverage(page: pymupdf.Page) -> tuple[float, float]:
    """Union raster avoids double counting overlapping images; subtract native text."""
    size = 256
    images = np.zeros((size, size), dtype=bool)
    text = np.zeros_like(images)
    for mask, rectangles in (
        (images, [pymupdf.Rect(item["bbox"]) for item in page.get_image_info()]),
        (text, [pymupdf.Rect(block[:4]) for block in page.get_text("blocks") if block[6] == 0]),
    ):
        for rectangle in rectangles:
            clip = rectangle & page.rect
            if clip.is_empty:
                continue
            x0 = int((clip.x0 - page.rect.x0) / page.rect.width * size)
            y0 = int((clip.y0 - page.rect.y0) / page.rect.height * size)
            x1 = min(size, int(np.ceil((clip.x1 - page.rect.x0) / page.rect.width * size)))
            y1 = min(size, int(np.ceil((clip.y1 - page.rect.y0) / page.rect.height * size)))
            mask[y0:y1, x0:x1] = True
    return float(images.mean()), float((images & ~text).mean())
