"""Recover native date fields overlaid on a blank document header line."""

import re
from dataclasses import dataclass
from datetime import date

_HEADER = re.compile(
    r"(?P<place>[^\W\d_][^\d,;:.!?\n]{1,59}),[ \t]+ngày[ \t]+tháng[ \t]+năm[ \t]+"
    r"(?P<year>(?:19|20)\d{2})\.?",
    re.IGNORECASE,
)
_NUMBER = re.compile(r"[0-9]+")


@dataclass(frozen=True)
class IssuedLine:
    header: int
    numbers: tuple[int, int]
    text: str
    value: date

    @property
    def positions(self) -> tuple[int, int, int]:
        return (self.header, *self.numbers)


def _native_bbox(block: dict) -> tuple[float, float, float, float] | None:
    bounds = block.get("bbox") or {}
    if (
        block.get("origin") != "native"
        or block.get("requires_review")
        or block.get("table")
        or bounds.get("units") != "normalized_0_1"
    ):
        return None
    x0, y0, x1, y1 = (bounds.get(k) for k in ("x0", "y0", "x1", "y1"))
    if None in (x0, y0, x1, y1) or not (0 <= x0 < x1 <= 1 and 0 <= y0 < y1 <= 1):
        return None
    return x0, y0, x1, y1


def _digits_on_line(
    blocks: list[dict], header: tuple[float, float, float, float]
) -> list[tuple[float, float, int, str]]:
    x0, y0, x1, y1 = header
    candidates = []
    for index, block in enumerate(blocks):
        text = block["text"].strip()
        if not _NUMBER.fullmatch(text) or (box := _native_bbox(block)) is None:
            continue
        left, top, right, bottom = box
        overlap = min(y1, bottom) - max(y0, top)
        if x0 < left < right < x1 and overlap >= (y1 - y0) * 0.8:
            candidates.append((left, right, index, text))
    return sorted(candidates)


def recover_issued_line(blocks: list[dict]) -> IssuedLine | None:
    matches = []
    for index, block in enumerate(blocks):
        if (header := _HEADER.fullmatch(block["text"].strip())) is None:
            continue
        bounds = _native_bbox(block)
        if bounds is None or bounds[3] > 0.3:
            continue
        candidates = _digits_on_line(blocks, bounds)
        if len(candidates) != 2 or candidates[0][1] >= candidates[1][0]:
            continue
        (_, _, day_index, day), (_, _, month_index, month) = candidates
        if len(day) > 2 or len(month) > 2:
            continue
        try:
            value = date(int(header["year"]), int(month), int(day))
        except ValueError:
            continue
        text = f"{header['place']}, ngày {day} tháng {month} năm {header['year']}"
        matches.append(IssuedLine(index, (day_index, month_index), text, value))
    return matches[0] if len(matches) == 1 else None
