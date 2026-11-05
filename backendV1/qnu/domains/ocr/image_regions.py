"""Find enclosed picture panels without inferring their text or arrow semantics."""

from collections import Counter
from math import ceil
from statistics import median

import pymupdf


def _threshold(data):
    histogram = Counter(data)
    total, weighted = len(data), sum(k * v for k, v in histogram.items())
    count = partial = 0
    best, threshold = -1, 0
    for level in range(256):
        count += histogram[level]
        partial += level * histogram[level]
        if not count or count == total:
            continue
        variance = (partial * total - weighted * count) ** 2 / (count * (total - count))
        if variance > best:
            best, threshold = variance, level
    return threshold


def _components(data, width, height, threshold):
    # Horizontal runs keep memory bounded by strokes, rather than one node/pixel.
    parents, runs, previous = [], [], []

    def root(index):
        while parents[index] != index:
            parents[index] = parents[parents[index]]
            index = parents[index]
        return index

    for y in range(height):
        current, x, start = [], 0, 0
        while x < width:
            if data[y * width + x] > threshold:
                x += 1
                continue
            left = x
            while x < width and data[y * width + x] <= threshold:
                x += 1
            index = len(runs)
            if index >= 200000:
                return []  # Highly textured images keep whole-image OCR only.
            parents.append(index)
            runs.append((left, y, x, y + 1, x - left))
            while start < len(previous) and runs[previous[start]][2] < left:
                start += 1
            for old in previous[start:]:
                if runs[old][0] > x:
                    break
                parents[root(old)] = root(index)
            current.append(index)
        previous = current
    boxes = {}
    for index, (x0, y0, x1, y1, pixels) in enumerate(runs):
        key = root(index)
        if key not in boxes:
            boxes[key] = [x0, y0, x1, y1, pixels]
        else:
            old = boxes[key]
            boxes[key] = [min(x0, old[0]), min(y0, old[1]), max(x1, old[2]), y1, old[4] + pixels]
    return list(boxes.values())


def panel_regions(page):
    """Keep the whole image plus interiors of sparse closed outlines containing glyphs.

    This supplements OCR layout detection; it does not assert that every picture
    is a diagram, or that its text has been read completely.
    """
    scale = min(1, 2048 / max(page.rect.width, page.rect.height))
    pixmap = page.get_pixmap(matrix=pymupdf.Matrix(scale, scale), colorspace=pymupdf.csGRAY)
    data, width, height = pixmap.samples, pixmap.width, pixmap.height
    parts = _components(data, width, height, _threshold(data))
    glyphs = [p for p in parts if p[4] >= 8 and p[2] - p[0] > 2 and p[3] - p[1] > 2]
    regions = [(0.0, 0.0, 1.0, 1.0)]
    if not glyphs:
        return regions
    unit = median(p[3] - p[1] for p in glyphs)
    for x0, y0, x1, y1, pixels in parts:
        w, h = x1 - x0, y1 - y0
        if w < unit * 4 or h < unit * 2 or pixels / (w * h) >= 0.25:
            continue
        inset = max(2, ceil(pixels / (w + h)))
        if not w > 2 * inset or not h > 2 * inset:
            continue
        enclosed = [
            p
            for p in glyphs
            if x0 + inset <= p[0] < p[2] <= x1 - inset and y0 + inset <= p[1] < p[3] <= y1 - inset
        ]
        if len(enclosed) < 2:
            continue
        regions.append(
            (
                (x0 + inset) / width,
                (y0 + inset) / height,
                (x1 - inset) / width,
                (y1 - inset) / height,
            )
        )
        if len(regions) == 65:
            break  # Retain whole-image OCR for any additional panels.
    return regions


def image_pdf(payload: bytes):
    """Return deterministic image-only PDF pages and their original-image mapping."""
    with pymupdf.open(stream=payload) as image, pymupdf.open() as document:
        original = image[0]
        source_width = pymupdf.Pixmap(payload).width
        resolution = pymupdf.Matrix(
            source_width / original.rect.width, source_width / original.rect.width
        )
        regions = panel_regions(original)
        for index, box in enumerate(regions):
            rectangle = pymupdf.Rect(
                *(
                    v * (original.rect.width if i % 2 == 0 else original.rect.height)
                    for i, v in enumerate(box)
                )
            )
            # Use original image resolution for OCR. The small grayscale pass above
            # is only for locating outlines, never an OCR input replacement.
            raster = (
                payload
                if index == 0
                else original.get_pixmap(matrix=resolution, clip=rectangle).tobytes("png")
            )
            page = document.new_page(width=rectangle.width, height=rectangle.height)
            page.insert_image(page.rect, stream=raster)
        return document.tobytes(no_new_id=True, deflate=True), regions
