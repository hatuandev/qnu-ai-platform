"""Reassemble font-fallback glyphs by baseline and spacing, without a vocabulary."""

import unicodedata
from collections import defaultdict
from statistics import median
from typing import Any


def reconstruct_layout_text(blocks: list[dict[str, Any]], clip: tuple[float, float, float, float] | None = None) -> str:
    baselines: dict[float, list[dict[str, Any]]] = defaultdict(list)
    for block in blocks:
        for line in block.get("lines", []):
            for span in line.get("spans", []):
                for char in span.get("chars", []):
                    if clip:
                        center_x = (char["bbox"][0] + char["bbox"][2]) / 2
                        center_y = (char["bbox"][1] + char["bbox"][3]) / 2
                        if not (clip[0] <= center_x <= clip[2] and clip[1] <= center_y <= clip[3]):
                            continue
                    if not char["c"].isspace():
                        baselines[round(char["origin"][1] * 2) / 2].append(char)
    lines = []
    for baseline in sorted(baselines):
        chars = sorted(baselines[baseline], key=lambda c: c["bbox"][0])
        widths = [c["bbox"][2] - c["bbox"][0] for c in chars if c["bbox"][2] > c["bbox"][0]]
        threshold = median(widths) * 0.35 if widths else 0
        result, right = [], None
        for char in chars:
            if right is not None and char["bbox"][0] - right > threshold:
                result.append(" ")
            result.append(char["c"])
            right = max(right or char["bbox"][2], char["bbox"][2])
        lines.append("".join(result))
    return unicodedata.normalize("NFC", "\n".join(lines))
