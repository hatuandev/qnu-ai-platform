"""Whitespace XY cuts keep independent columns together, with no content keywords."""


def _gap(blocks, axis):
    intervals = sorted((b.bbox[axis], b.bbox[axis + 2]) for b in blocks)
    end = intervals[0][1]
    gaps = []
    for start, stop in intervals[1:]:
        if start > end + 1e-6:
            gaps.append((start - end, (start + end) / 2))
        end = max(end, stop)
    return max(gaps, default=(0, None))


def reading_order(blocks):
    if len(blocks) < 2:
        return list(blocks)
    pending, result = [list(blocks)], []
    while pending:
        group = pending.pop()
        if len(group) < 2:
            result.extend(group)
            continue
        _, vertical = _gap(group, 0)
        _, horizontal = _gap(group, 1)
        axis, cut = (0, vertical) if vertical is not None else (1, horizontal)
        if cut is None:
            result.extend(sorted(group, key=lambda b: (b.bbox[1], b.bbox[0], b.order)))
            continue
        left = [b for b in group if b.bbox[axis] < cut]
        right = [b for b in group if b.bbox[axis] >= cut]
        pending.extend([right, left])
    return result
