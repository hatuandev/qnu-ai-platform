"""Extract and verify source-bound schedule events."""

import re
from datetime import date

from pydantic import ValidationError

from qnu.domains.knowledge.metadata import EventKind, EventMoment, EventValue, RelativeDeadline

INTAKE_LABEL = r"\b(?:đợt|kỳ)\s*(?:tuyển\s+sinh\s*)?(?:\d{1,2}|[IVX]{1,4})(?!\w)"
EVENT_INTAKE = re.compile(f"({INTAKE_LABEL})", re.IGNORECASE)
EVENT_BOUNDARY = (
    r"(?=\s*(?:ngày|từ|trước|vào|là|đến|tại|trong|trên|và|diễn\s+ra|\d|[(:：,;.\n]|"
    + INTAKE_LABEL
    + r"|$))"
)
EVENT_LABELS = (
    (
        "fee_deadline",
        re.compile(
            r"(?:(?:thời\s+(?:gian|hạn)\s+|hạn\s+(?:cuối\s+)?)?(?:nộp|đóng|thanh\s+toán)"
            r"\s+(?:lệ\s+phí|phí)(?:\s+(?:xét\s+tuyển|dự\s+thi|đăng\s+ký))?"
            r"(?:\s+trực\s+(?:tuyến|tiếp))?)" + EVENT_BOUNDARY,
            re.IGNORECASE,
        ),
    ),
    (
        "enrollment_confirmation",
        re.compile(
            r"(?:(?:thời\s+(?:gian|hạn)\s+|hạn\s+(?:cuối\s+)?)?xác\s+nhận\s+nhập\s+học"
            r"(?:\s+trực\s+(?:tuyến|tiếp))?)" + EVENT_BOUNDARY,
            re.IGNORECASE,
        ),
    ),
    (
        "registration_deadline",
        re.compile(
            r"(?:hạn\s+(?:cuối\s+|chót\s+)?(?:nộp|đăng\s+ký|nhận|xác\s+nhận(?!\s+nhập\s+học)|"
            r"hoàn\s+thiện|ghi\s+danh)(?:\s+(?:hồ\s+sơ|xét\s+tuyển|nhập\s+học|dự\s+tuyển))?"
            r"|thời\s+hạn\s+(?:đăng\s+ký|nộp|hoàn\s+thiện|xác\s+nhận(?!\s+nhập\s+học))"
            r"|thời\s+gian\s+(?:đăng\s+ký|nhận|nộp)(?:\s+hồ\s+sơ)?"
            r"|đăng\s+ký\s+(?:thông\s+tin\s+)?(?:xét\s+tuyển|dự\s+tuyển|nhập\s+học|xét\s+học\s+bạ|"
            r"tuyển\s+sinh)(?:\s+trực\s+tuyến|\s+trực\s+tiếp)?"
            r"|(?:thời\s+gian\s+)?đăng\s+ký\s+(?:dự\s+thi(?:\s+năng\s+khiếu)?|thi\s+năng\s+khiếu)"
            r"|nhận\s+hồ\s+sơ(?:\s+đăng\s+ký|\s+xét\s+tuyển)?"
            r"|gia\s+hạn\s+(?:thời\s+gian\s+)?(?:đăng\s+ký|nộp|xác\s+nhận))" + EVENT_BOUNDARY,
            re.IGNORECASE,
        ),
    ),
    (
        "exam_date",
        re.compile(
            r"(?:ngày\s+thi|thời\s+gian\s+thi|lịch\s+thi|ngày\s+tổ\s+chức\s+thi"
            r"|(?:ngày\s+thi|thời\s+gian\s+thi|lịch\s+thi|tổ\s+chức\s+thi)\s+năng\s+khiếu"
            r"(?:\s+dành\s+cho\s+[^,.;\n]{3,120}?(?=\s+(?:vào|từ|ngày)\s+))?"
            r"|tổ\s+chức\s+thi\s+tuyển\s+sinh"
            r"|(?:^|(?<=\)))[ \t]*thi\s+năng\s+khiếu(?:[ \t]+[^:;.\n]{2,60}?)?"
            r"(?=[ \t]*:[ \t]*(?:thi|vào|ngày)\b)"
            r"|ngày\s+kiểm\s+tra\s+(?:năng\s+lực|tư\s+duy|đánh\s+giá)"
            r"|kỳ\s+thi\s+(?:đánh\s+giá\s+năng\s+lực|tuyển\s+sinh))" + EVENT_BOUNDARY,
            re.IGNORECASE,
        ),
    ),
    (
        "result_date",
        re.compile(
            r"(?:ngày\s+(?:công\s+bố|thông\s+báo|trả)\s+kết\s+quả"
            r"|(?:lịch|thời\s+gian)\s+(?:công\s+bố|thông\s+báo)\s+kết\s+quả"
            r"|công\s+bố\s+kết\s+quả(?:\s+xét\s+tuyển)?"
            r"|công\s+bố\s+điểm\s+chuẩn|ngày\s+công\s+bố\s+điểm\s+chuẩn)" + EVENT_BOUNDARY,
            re.IGNORECASE,
        ),
    ),
)
WRITTEN_FULL_DATE = re.compile(r"ngày\s+(\d{1,2})\s+tháng\s+(\d{1,2})\s+năm\s+(\d{4})(?!\d)")
FULL_DATE = re.compile(r"(?:ngày\s+)?(\d{1,2})\s*([/.-])\s*(\d{1,2})\s*\2\s*(\d{4})(?!\d)")
MONTH_YEAR = re.compile(r"tháng\s+(\d{1,2})\s*(?:năm\s+|/\s*)(\d{4})(?!\d)")
WRITTEN_PARTIAL_DATE = re.compile(r"ngày\s+(\d{1,2})\s+tháng\s+(\d{1,2})(?!\s*năm)")
DAY_MONTH = re.compile(r"(?<![\d/.-])(\d{1,2})\s*([/.])\s*(\d{1,2})(?![\d/]|[.-]\s*\d)")
EVENT_TIME = re.compile(
    r"(?<!\d)([01]?\d|2[0-3])\s*(?:[:h]|giờ)\s*([0-5]\d)(?![\d/]|[.-]\s*\d)",
    re.IGNORECASE,
)
RANGE_BETWEEN = re.compile(r"^\s*(?:đến|tới|hết|[-–—])\s*(?P<before>trước\s+)?$", re.IGNORECASE)
LISTED_DAYS = re.compile(
    r"\bcác\s+ngày\s+((?:\d{1,2}\s*,\s*){0,29}\d{1,2})(?:\s*,\s*|\s+(?:và|&)\s+)"
    r"(\d{1,2})/(\d{1,2})/(\d{4})(?![\d/])",
    re.IGNORECASE,
)
START_CUE = re.compile(r"\b(?:từ|kể\s+từ|bắt\s+đầu\s+từ)\b", re.IGNORECASE)
TRAILING_RANGE = re.compile(r"\b(?:đến|tới)(?:\s+trước)?$", re.IGNORECASE)
RELATIVE_DEADLINE = re.compile(
    r"(?:trong\s+vòng|không\s+quá|chậm\s+nhất(?:\s+là)?|tối\s+đa|sau|trước)\s+"
    r"(\d{1,3})\s+(ngày\s+làm\s+việc|tuần|tháng|ngày)\b"
    r"\s+(?:kể\s+từ|tính\s+từ|sau)\s+([^,.;\n]{3,160})",
    re.IGNORECASE,
)
RELATIVE_UNITS = {
    "ngày": "day",
    "ngày làm việc": "working_day",
    "tuần": "week",
    "tháng": "month",
}
EXTENSION_CUE = re.compile(
    r"\b(gia\s+hạn|kéo\s+dài|thay\s+thế|thay\s+cho|thay\s+lịch|điều\s+chỉnh)\b",
    re.IGNORECASE,
)
EVENT_AUDIENCE = re.compile(
    r"(?:dành\s+cho|áp\s+dụng\s+cho|đối\s+tượng)\s*[:：]?\s*([^,.;\n]{3,120}?)"
    r"(?=\s+vào\s+|\s+từ\s+|[,.\n;]|$)",
    re.IGNORECASE,
)
EVENT_METHOD = re.compile(
    r"(?:phương\s+thức|hình\s+thức)\s*[:：]?\s*([^,.;\n]{3,120})", re.IGNORECASE
)
EVENT_CHANNEL = re.compile(
    r"\b((?:(?:trực\s+tuyến\s+)?trên\s+|tại\s+(?=https?://)).{3,120}?)"
    r"(?=\s+(?:từ|đến|trước|ngày|trong\s+khoảng|là)\s+)",
    re.IGNORECASE,
)
EVENT_CLAUSE = re.compile(r"\b((?:mục|khoản|điều|phần)\s+\d+(?:\.\d+)*)\b", re.IGNORECASE)
CLAUSE_BOUNDARY = re.compile(
    rf"[;\n]+|(?<=\.)[ \t]+(?=[^\W\d_])|,\s*(?={INTAKE_LABEL}\s*[:：])", re.IGNORECASE
)
INTAKE_CONTINUATION = re.compile(
    rf"^({INTAKE_LABEL})\s*[:：]\s*(?=từ\b|đến\b|trước\b|ngày\b|\d)", re.IGNORECASE
)


def _moment_spans(text: str) -> list[tuple[int, int, EventMoment]]:
    spans = []
    for regex, build in (
        (
            WRITTEN_FULL_DATE,
            lambda m: EventMoment(date=date(int(m[3]), int(m[2]), int(m[1]))),
        ),
        (FULL_DATE, lambda m: EventMoment(date=date(int(m[4]), int(m[3]), int(m[1])))),
        (MONTH_YEAR, lambda m: EventMoment(month=int(m[1]), year=int(m[2]))),
        (WRITTEN_PARTIAL_DATE, lambda m: EventMoment(month=int(m[2]), day=int(m[1]))),
        (DAY_MONTH, lambda m: EventMoment(month=int(m[3]), day=int(m[1]))),
    ):
        for match in regex.finditer(text):
            try:
                spans.append((match.start(), match.end(), build(match)))
            except (ValueError, ValidationError):
                continue
    spans.sort(key=lambda span: (span[0], -(span[1] - span[0])))
    kept: list[tuple[int, int, EventMoment]] = []
    for span in spans:
        if any(start <= span[0] and span[1] <= end for start, end, _ in kept):
            continue
        kept.append(span)
    return kept


def _scope_literal(pattern: re.Pattern, segment: str, limit: int) -> str | None:
    found = {match.group(1).strip(" \t,.;:") for match in pattern.finditer(segment)}
    found.discard("")
    if len(found) != 1:
        return None
    return next(iter(found))[:limit]


def _listed_dates(window: str, match: re.Match) -> list[date] | None:
    # The common month/year must be stated on the last day of the same explicit list.
    spans = _moment_spans(window)
    if len(spans) != 1 or not match.start() <= spans[0][0] < match.end():
        return None
    try:
        days = [*re.findall(r"\d+", match[1]), match[2]]
        return [date(int(match[4]), int(match[3]), int(day)) for day in days]
    except ValueError:
        return None


def _clock(match: re.Match) -> str:
    return f"{int(match[1]):02d}:{match[2]}"


def _event_value(kind: EventKind, label: str, window: str, prefix: str) -> EventValue | None:
    start_moment = end_moment = dates = relative = end_exclusive = None
    time_matches = list(EVENT_TIME.finditer(window))
    # A relative deadline names its anchor event, which must not split the clause.
    relative_match = RELATIVE_DEADLINE.search(window)
    if relative_match:
        value = int(relative_match.group(1))
        unit = RELATIVE_UNITS[" ".join(relative_match.group(2).casefold().split())]
        from_event = relative_match.group(3).strip(" \t,.;:")[:200]
        if not from_event:
            return None
        relative = RelativeDeadline(value=value, unit=unit, from_event=from_event)
    elif listed := LISTED_DAYS.search(window):
        dates = _listed_dates(window, listed)
        if dates is None or time_matches:
            return None
    else:
        spans = _moment_spans(window)
        if not spans or TRAILING_RANGE.search(window.rstrip(" .;")):
            return None
        if len(spans) >= 2:
            if len(spans) != 2:
                return None
            (start_at, first_end, start_moment), (end_at, _, end_moment) = spans
            head_clock = [match for match in time_matches if match.end() <= start_at]
            tail_clock = [match for match in time_matches if first_end <= match.start() < end_at]
            if (
                len(head_clock) > 1
                or len(tail_clock) > 1
                or len(time_matches) != len(head_clock) + len(tail_clock)
            ):
                return None
            connector_end = tail_clock[0].start() if tail_clock else end_at
            if tail_clock and window[tail_clock[0].end() : end_at].strip():
                return None
            connector = window[first_end:connector_end]
            bridge = RANGE_BETWEEN.fullmatch(connector)
            if bridge is None:
                return None
            end_exclusive = True if bridge["before"] else None
            if head_clock:
                start_moment = start_moment.model_copy(update={"time": _clock(head_clock[0])})
            if tail_clock:
                end_moment = end_moment.model_copy(update={"time": _clock(tail_clock[0])})
        else:
            if len(time_matches) > 1:
                return None
            moment = spans[0][2]
            if time_matches:
                moment = moment.model_copy(update={"time": _clock(time_matches[0])})
            if kind in {
                "registration_deadline",
                "fee_deadline",
                "enrollment_confirmation",
            } and START_CUE.search(window[: spans[0][0]]):
                start_moment = moment
            else:
                end_moment = moment
    cue = EXTENSION_CUE.search(window)
    local_intakes = {match[1].casefold() for match in EVENT_INTAKE.finditer(window)}
    if len(local_intakes) > 1:
        return None
    intake = _scope_literal(EVENT_INTAKE, window, 120) or _scope_literal(EVENT_INTAKE, prefix, 120)
    try:
        return EventValue(
            kind=kind,
            label=label,
            moment=end_moment,
            window_start=start_moment,
            relative=relative,
            dates=dates,
            end_exclusive=end_exclusive,
            intake=intake,
            audience=_scope_literal(EVENT_AUDIENCE, window, 160),
            method=_scope_literal(EVENT_CHANNEL, window, 160)
            or _scope_literal(EVENT_METHOD, window, 160),
            clause=_scope_literal(EVENT_CLAUSE, window, 160),
            note=cue.group(1).strip()[:120] if cue is not None else None,
        )
    except ValidationError:
        return None


def extract_events(quote: str) -> list[tuple[EventValue, str]]:
    """Extract labelled schedules; an unlabeled or ambiguous date proves nothing."""
    if len(quote) > 2000 or not re.search(r"\d", quote):
        return []
    proposals = []
    cursor = proof_start = 0
    previous = None
    for fragment in CLAUSE_BOUNDARY.split(quote):
        start = quote.index(fragment, cursor)
        cursor = start + len(fragment)
        segment = fragment.strip()
        events = _labelled_events(segment)
        if events:
            proof_start = start
        elif (
            previous
            and previous.intake
            and (intake := INTAKE_CONTINUATION.match(segment))
            and previous.intake.casefold() != intake[1].casefold()
        ):
            event = _event_value(previous.kind, previous.label, segment, "")
            events = [event] if event else []
        previous = events[0] if len(events) == 1 else None
        proposals.extend((event, quote[proof_start:cursor].strip()) for event in events)
    return proposals


def _labelled_events(segment: str) -> list[EventValue]:
    relative = list(RELATIVE_DEADLINE.finditer(segment))
    labels = sorted(
        (
            (kind, match)
            for kind, pattern in EVENT_LABELS
            for match in pattern.finditer(segment)
            if not any(anchor.start(3) <= match.start() < anchor.end(3) for anchor in relative)
        ),
        key=lambda item: item[1].start(),
    )
    prefix = segment[: labels[0][1].start()] if labels else ""
    events = []
    for position, (kind, match) in enumerate(labels):
        end = labels[position + 1][1].start() if position + 1 < len(labels) else len(segment)
        event = _event_value(kind, match.group(0), segment[match.start() : end], prefix)
        if event is not None:
            events.append(event)
    return events


def event_proved(event: EventValue, quotes: list[str]) -> bool:
    """Require the requested type, dates and scope to belong to one source event."""
    fields = event.model_dump(exclude={"label"}, exclude_none=True)
    label = " ".join(event.label.casefold().split())
    return any(
        label in " ".join(extracted.label.casefold().split())
        and fields == extracted.model_dump(exclude={"label"}, exclude_none=True)
        for quote in quotes
        for extracted, _ in extract_events(quote)
    )


def fragmented_windows(blocks: list[dict]) -> dict[int, tuple[int, EventValue]]:
    """Find disjoint, complete schedule sentences cut into OCR text blocks."""
    windows = {}
    consumed = 0
    for start, block in enumerate(blocks):
        head = _fragment(block)
        if (
            start < consumed
            or not head
            or head.endswith((".", ";", "!", "?"))
            or not any(pattern.search(head) for _, pattern in EVENT_LABELS)
        ):
            continue
        complete = [event for event, _ in extract_events(head)]
        unfinished = CLAUSE_BOUNDARY.split(head)[-1].strip()
        text = head
        for end in range(start + 1, min(start + 3, len(blocks))):
            tail = _fragment(blocks[end])
            if not tail or not (
                tail[:1].islower() or (tail[:1].isdigit() and TRAILING_RANGE.search(text))
            ):
                break
            text += " " + tail
            if not tail.endswith((".", ";")):
                continue
            found = [
                event
                for event, quote in extract_events(text)
                if event.window_start
                and event.moment
                and event not in complete
                and (
                    (quote == text and event.label.strip() in head)
                    or (complete and unfinished and quote.startswith(unfinished) and quote != head)
                )
            ]
            if len(found) == 1:
                windows[start] = (end + 1, found[0])
                consumed = end + 1
            break
    return windows


def _fragment(block: dict) -> str:
    if (
        block.get("table")
        or block.get("requires_review")
        or block.get("type")
        in {
            "figure",
            "title",
            "heading",
            "section-header",
        }
    ):
        return ""
    return block["text"].strip()


def fragmented_proofs(documents: list[dict]):
    for document in documents:
        run = document["ocr_run_id"]
        for page in document["pages"]:
            blocks = page["blocks"]
            for start, (end, event) in fragmented_windows(blocks).items():
                yield (
                    event,
                    [
                        {"citation": f"{run}:{block['evidence_id']}", "quote": _fragment(block)}
                        for block in blocks[start:end]
                    ],
                )
