"""Unit tests for SmartLayoutDetector: verifying no list label and closing page signature seal unification."""

from __future__ import annotations

import io

import numpy as np
from PIL import Image

from app.modules.ocr.layout_detector import SmartLayoutDetector


def _create_synthetic_closing_page() -> bytes:
    """Create a synthetic page image (800x1200) representing page 23 of quy che dao tao.

    - Paragraph 1-3: Regular text clauses.
    - Paragraph 4: Full-width clause spanning across the width.
    - Bottom Right: Official Red Seal + Signer Title ('HIỆU TRƯỞNG') + Signer Name.
    """
    img = Image.new("RGB", (800, 1200), color=(255, 255, 255))
    arr = np.array(img)

    # 1. Text blocks: simulate horizontal ink text (dark pixels)
    # Paragraph 1 (y: 100-180)
    arr[100:180, 80:720] = 30
    # Paragraph 2 (y: 220-300)
    arr[220:300, 80:720] = 30
    # Paragraph 3 (y: 340-420)
    arr[340:420, 80:720] = 30
    # Paragraph 4: Full width (y: 460-560)
    arr[460:560, 80:720] = 30

    # 2. Signer Title 'HIỆU TRƯỞNG' (y: 720-750, x: 450-650)
    arr[720:750, 450:650] = 30

    # 3. Red Stamp / Seal in bottom right (y: 780-920, x: 400-540)
    # Circular red seal in RGB: high red (220), low green/blue (30)
    cy, cx = 850, 470
    radius = 65
    y_indices, x_indices = np.ogrid[:1200, :800]
    dist_from_center = np.sqrt((x_indices - cx) ** 2 + (y_indices - cy) ** 2)
    # Draw ring and text inside seal
    seal_ring = (dist_from_center >= radius - 6) & (dist_from_center <= radius)
    seal_inner = (dist_from_center < radius - 15) & (dist_from_center > 20)
    red_pixels = seal_ring | (seal_inner & ((x_indices + y_indices) % 5 == 0))
    arr[red_pixels] = [220, 30, 30]

    # 4. Signer Name 'PGS.TS. Đỗ Ngọc Mỹ' (y: 950-980, x: 440-660)
    arr[950:980, 440:660] = 30

    out_img = Image.fromarray(arr)
    buf = io.BytesIO()
    out_img.save(buf, format="JPEG", quality=90)
    return buf.getvalue()


def test_no_list_label_and_correct_signature_box():
    detector = SmartLayoutDetector()
    img_bytes = _create_synthetic_closing_page()

    regions = detector.detect_layout_regions(
        image_input=img_bytes,
        markdown_text="",
        page_number=23,
    )

    assert len(regions) > 0

    # 1. Verification: NO 'list' label should exist in detected regions
    labels = [r["type"] for r in regions]
    assert "list" not in labels, f"Found unexpected 'list' label in regions: {labels}"

    # 2. Verification: Exactly ONE signature block should be detected
    sig_regions = [r for r in regions if r["type"] == "signature"]
    assert len(sig_regions) == 1, f"Expected exactly 1 signature region, found {len(sig_regions)}"

    sig = sig_regions[0]
    # Signature box MUST enclose the red seal (y around 70-85%)
    assert sig["top"] >= 55.0, f"Signature top too high: {sig['top']}%"
    assert sig["top"] <= 75.0, f"Signature top should start around signer title: {sig['top']}%"
    # Signature bottom MUST cover the red seal and signer name (y >= 78%)
    sig_bottom = sig["top"] + sig["height"]
    assert sig_bottom >= 78.0, f"Signature bottom too shallow: {sig_bottom}%"
    # Signature MUST be located in the right half of the page
    assert sig["left"] >= 35.0, f"Signature should be on right half: {sig['left']}%"

    # 3. Verification: Paragraph 4 (y: 460-560 -> top ~38-47%) must remain an intact TEXT block
    p4_regions = [
        r for r in regions
        if r["type"] == "text" and 35.0 <= r["top"] <= 52.0
    ]
    assert len(p4_regions) >= 1, "Paragraph 4 should remain as text block"
    # Paragraph 4 must NOT be cut into half width
    for p4 in p4_regions:
        assert p4["width"] >= 50.0, f"Paragraph 4 width was improperly split: {p4['width']}%"
