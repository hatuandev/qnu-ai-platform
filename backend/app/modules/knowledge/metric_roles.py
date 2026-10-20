"""Conservative compositional quantity roles, without document-specific labels."""

import re
import unicodedata

ATTRIBUTES = {'quota': 'expected_quota', 'reported_count': 'reported_count',
              'estimate': 'estimated_count', 'rate': 'rate'}


def metric_role_evidence(header: str) -> tuple[str | None, str | None]:
    text = ' '.join(unicodedata.normalize('NFC', header).casefold().split())
    quota = re.search(r'\b(?:chỉ tiêu|quota|số lượng tuyển(?: sinh)?)\b', text)
    recorded = re.search(r'\b(?:ghi nhận|đã ghi nhận|reported|recorded)\b', text)
    estimate = re.search(r'\b(?:ước tính|dự báo|estimated|forecast)\b', text)
    count = re.search(r'\b(?:số lượng|count)\b', text)
    rate = re.search(r'\b(?:tỷ lệ|tỉ lệ|rate|percentage)\b', text)
    if quota and (recorded or estimate):
        return None, None
    if quota:
        return 'quota', quota.group()
    if rate:
        return 'rate', rate.group()
    if estimate:
        return 'estimate', estimate.group()
    if recorded and count:
        return 'reported_count', recorded.group()
    return None, None


def header_unit(header: str) -> str | None:
    units = re.findall(r'\(([^()]+)\)', header)
    return units[-1].strip() if len(units) == 1 else None
