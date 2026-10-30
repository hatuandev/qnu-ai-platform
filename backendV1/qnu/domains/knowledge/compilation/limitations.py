"""Retain observable extraction limits without guessing unread source content."""

from pydantic import ValidationError

from qnu.domains.knowledge.compilation.schemas import DraftContent
from qnu.platform.errors import AppException


def limitation_paragraphs(documents: list[dict]) -> list[dict]:
    paragraphs = []
    for doc in documents:
        for page in doc["pages"]:
            for block in page["blocks"]:
                table = block.get("table")
                if (
                    not block.get("requires_review")
                    or block["text"].strip()
                    or (table and table.get("status") == "parsed" and table.get("rows"))
                ):
                    continue
                paragraphs.append(
                    {
                        "text": (
                            f"Khối nguồn được trích dẫn tại trang {page['page_number']} "
                            "chưa có văn bản trích xuất và đang được đánh dấu cần kiểm tra. "
                            "Chưa xác định nội dung khối này từ dữ liệu đã cấp; cần đối chiếu "
                            "nguồn để xác định phần chưa đọc được. Giới hạn này chỉ áp dụng "
                            "cho khối được trích dẫn, không kết luận về các khối khác cùng trang."
                        ),
                        "citations": [f"{doc['ocr_run_id']}:{block['evidence_id']}"],
                    }
                )
    return paragraphs


def retain_limitations(draft: DraftContent, documents: list[dict]) -> DraftContent:
    content = draft.model_dump()
    existing = {
        (paragraph["text"], tuple(paragraph["citations"]))
        for section in content["sections"]
        for paragraph in section["paragraphs"]
    }
    missing = [
        paragraph
        for paragraph in limitation_paragraphs(documents)
        if (paragraph["text"], tuple(paragraph["citations"])) not in existing
    ]
    for offset in range(0, len(missing), 100):
        content["sections"].append(
            {
                "heading": "Giới hạn dữ liệu trích xuất",
                "paragraphs": missing[offset : offset + 100],
            }
        )
    try:
        return DraftContent.model_validate(content)
    except ValidationError as exc:
        raise AppException(
            "Không đủ dung lượng cấu trúc để giữ đầy đủ giới hạn trích xuất.",
            code="compilation_source_limits_exceeded",
            status_code=422,
        ) from exc
