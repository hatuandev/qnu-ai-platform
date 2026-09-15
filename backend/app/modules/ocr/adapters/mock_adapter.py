"""Mock OCR Adapter for Unit Testing & Resilient Fallback."""

from __future__ import annotations

from typing import Any

from app.modules.ocr.adapters.base import BaseOCRAdapter


class MockOCRAdapter(BaseOCRAdapter):
    """Fallback / testing OCR adapter returning deterministic simulated text."""

    @property
    def name(self) -> str:
        return "mock_ocr"

    @property
    def display_name(self) -> str:
        return "Mock High-Fidelity OCR Adapter"

    def is_available(self) -> bool:
        return True

    async def extract(self, content: bytes, filename: str) -> dict[str, Any]:
        mock_text = (
            f"TÀI LIỆU QUY CHẾ ĐÀO TẠO ĐẠI HỌC QUY NHƠN\n"
            f"Văn bản: {filename}\n"
            f"Trang 1: Điều 1. Phạm vi điều chỉnh và đối tượng áp dụng.\n"
            f"Quy chế này áp dụng cho toàn thể sinh viên chính quy các khóa.\n"
            f"Trang 2: Điều 2. Thang điểm đánh giá và xếp loại học lực.\n"
            f"Điểm chuẩn đầu ra ngoại ngữ B1, chứng chỉ công nghệ thông tin cơ bản."
        )
        pages = [
            {
                "page_number": 1,
                "extracted_text": "Điều 1. Phạm vi điều chỉnh và đối tượng áp dụng.\nQuy chế này áp dụng cho toàn thể sinh viên chính quy các khóa.",
                "confidence": 0.98,
                "word_count": 22,
                "line_count": 2,
                "has_tables": False,
            },
            {
                "page_number": 2,
                "extracted_text": "Điều 2. Thang điểm đánh giá và xếp loại học lực.\nĐiểm chuẩn đầu ra ngoại ngữ B1, chứng chỉ công nghệ thông tin cơ bản.",
                "confidence": 0.96,
                "word_count": 24,
                "line_count": 2,
                "has_tables": False,
            },
        ]
        return {
            "engine_used": self.name,
            "total_pages": 2,
            "overall_confidence": 0.97,
            "pages": pages,
            "raw_text": mock_text,
        }
