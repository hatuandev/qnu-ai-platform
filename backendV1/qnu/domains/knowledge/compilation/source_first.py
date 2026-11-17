"""Assemble a draft from the pinned text without asking a model to rewrite it."""

from pydantic import ValidationError

from qnu.domains.knowledge.compilation.drafting import validated_draft
from qnu.domains.knowledge.compilation.issued_line import recover_issued_line
from qnu.domains.knowledge.compilation.quality import (
    CONFIRMED_BY_SOURCE,
    PARTIALLY_CHECKED,
    quality_validation,
)
from qnu.domains.knowledge.compilation.schemas import DRAFT_PARAGRAPH_TEXT_LIMIT, DraftContent
from qnu.domains.knowledge.event_schedule import fragmented_windows
from qnu.platform.errors import AppException


def build_source_draft(topic: str, documents: list[dict], run_id: str) -> dict:
    sections = []
    checks = []
    for number, document in enumerate(documents, start=1):
        paragraphs = []
        for page in document["pages"]:
            blocks = page["blocks"]
            windows = fragmented_windows(blocks)
            issued = recover_issued_line(blocks) if page.get("page_number") == 1 else None
            consumed = 0
            for index, block in enumerate(blocks):
                if index < consumed:
                    continue
                if issued and index in issued.positions:
                    if index == issued.header:
                        paragraphs.append(
                            {
                                "text": issued.text,
                                "citations": [
                                    f"{document['ocr_run_id']}:{blocks[i]['evidence_id']}"
                                    for i in issued.positions
                                ],
                            }
                        )
                    continue
                if index in windows:
                    consumed = windows[index][0]
                    fragments = blocks[index:consumed]
                    paragraphs.append(
                        {
                            "text": "\n".join(part["text"] for part in fragments),
                            "citations": [
                                f"{document['ocr_run_id']}:{part['evidence_id']}"
                                for part in fragments
                            ],
                        }
                    )
                    continue
                ref = f"{document['ocr_run_id']}:{block['evidence_id']}"
                text = block["text"]
                table = block.get("table")
                if (
                    not text.strip()
                    and table
                    and table.get("status") == "parsed"
                    and table.get("rows")
                ):
                    text = f"Bảng nguồn tại trang {page['page_number']} (xem phần Bảng nguồn)."
                if text.strip():
                    paragraphs.extend(
                        {
                            "text": text[offset : offset + DRAFT_PARAGRAPH_TEXT_LIMIT],
                            "citations": [ref],
                        }
                        for offset in range(0, len(text), DRAFT_PARAGRAPH_TEXT_LIMIT)
                    )
                    if block.get("requires_review"):
                        checks.append(
                            {
                                "text": f"Đối chiếu khối nguồn đã được đánh dấu tại trang {page['page_number']}.",
                                "citations": [ref],
                            }
                        )
        for offset in range(0, len(paragraphs), 100):
            sections.append(
                {
                    "heading": f"Nguồn {number} · Phần {offset // 100 + 1}",
                    "paragraphs": paragraphs[offset : offset + 100],
                }
            )
    for offset in range(0, len(checks), 100):
        sections.append(
            {"heading": "Cần đối chiếu nguồn", "paragraphs": checks[offset : offset + 100]}
        )
    if not sections:
        raise AppException(
            "Nguồn đã chọn chưa có văn bản hoặc bảng để biên soạn.",
            code="compilation_draft_empty",
            status_code=422,
        )
    try:
        content = DraftContent(title=topic[:500], sections=sections, unknowns=[])
    except ValidationError as exc:
        raise AppException(
            "Không đủ dung lượng cấu trúc để giữ đầy đủ nội dung nguồn.",
            code="compilation_source_limits_exceeded",
            status_code=422,
        ) from exc
    draft = validated_draft(content, topic, documents, run_id)
    draft["validation"]["source_copy"] = "retained"
    draft["validation"]["quality"] = quality_validation(
        source_binding=CONFIRMED_BY_SOURCE,
        coverage=PARTIALLY_CHECKED,
    )
    return draft
