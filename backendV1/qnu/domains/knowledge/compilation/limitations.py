"""Retain observable extraction limits without guessing unread source content."""

from pydantic import ValidationError

from qnu.domains.knowledge.compilation.schemas import DraftContent
from qnu.platform.errors import AppException


def _linked_image_text(block: dict, page: dict) -> list[dict]:
    asset = (block.get("image") or {}).get("asset_no")
    if type(asset) is not int or asset <= 0:
        return []
    return [
        other
        for other in page["blocks"]
        if other is not block
        and other.get("source_image_asset_no") == asset
        and (
            other.get("text", "").strip()
            or (
                (table := other.get("table"))
                and table.get("status") == "parsed"
                and any(c.get("text", "").strip() for row in table.get("rows", []) for c in row)
            )
        )
    ]


def _image_limits(block: dict, page: dict, run_id: str) -> list[dict]:
    linked = _linked_image_text(block, page)
    if not linked:
        return []
    references = list(dict.fromkeys(f"{run_id}:{item['evidence_id']}" for item in linked))
    # Each paragraph fits the draft citation contract without dropping linked OCR.
    return [
        {
            "text": (
                f"Ảnh nguồn được trích dẫn tại trang {page['page_number']} "
                "đã có văn bản OCR trong các khối liên kết được dẫn chứng. "
                "Chưa xác minh độ chính xác, độ đầy đủ của chữ và quan hệ bố cục "
                "trong ảnh; cần đối chiếu ảnh gốc. Cảnh báo này không kết luận "
                "ảnh chưa được OCR hoặc các khối khác cùng trang chưa được đọc."
            ),
            "citations": [f"{run_id}:{block['evidence_id']}", *references[offset : offset + 99]],
        }
        for offset in range(0, len(references), 99)
    ]


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
                if notes := _image_limits(block, page, doc["ocr_run_id"]):
                    paragraphs.extend(notes)
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
