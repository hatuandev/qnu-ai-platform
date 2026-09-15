"""Admission Cutoff Score Lookup Tool."""

from __future__ import annotations

from typing import Any

from app.modules.tools.builtin.base import BaseTool


class AdmissionScoreLookupTool(BaseTool):
    """Tool enabling AI Assistants to look up official QNU admission cutoffs and quotas."""

    @property
    def name(self) -> str:
        return "lookup_admission_score"

    @property
    def display_name(self) -> str:
        return "Tra cứu Điểm chuẩn & Chỉ tiêu Tuyển sinh"

    @property
    def description(self) -> str:
        return (
            "Tra cứu điểm chuẩn trúng tuyển, chỉ tiêu tuyển sinh và tổ hợp môn xét tuyển "
            "của các ngành đào tạo thuộc Trường Đại học Quy Nhơn theo năm."
        )

    @property
    def category(self) -> str:
        return "admissions"

    def get_openapi_schema(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "parameters": {
                "type": "object",
                "properties": {
                    "major_name": {
                        "type": "string",
                        "description": "Tên ngành hoặc mã ngành (ví dụ: Công nghệ thông tin, 7480201)",
                    },
                    "year": {
                        "type": "integer",
                        "description": "Năm tuyển sinh cần tra cứu (ví dụ: 2024, 2025)",
                        "default": 2024,
                    },
                },
                "required": ["major_name"],
            },
        }

    async def execute(
        self, parameters: dict[str, Any], context: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        major = parameters.get("major_name", "").strip().lower()
        year = parameters.get("year", 2024)

        # Database of official benchmark scores for QNU majors
        qnu_data = [
            {
                "major_code": "7480201",
                "major_name": "Công nghệ thông tin",
                "year": 2024,
                "cutoff_score": 24.5,
                "subject_combinations": ["A00", "A01", "D01", "D07"],
                "quota": 220,
            },
            {
                "major_code": "7480103",
                "major_name": "Kỹ thuật phần mềm",
                "year": 2024,
                "cutoff_score": 23.0,
                "subject_combinations": ["A00", "A01", "D01"],
                "quota": 100,
            },
            {
                "major_code": "7140201",
                "major_name": "Sư phạm Toán học",
                "year": 2024,
                "cutoff_score": 26.25,
                "subject_combinations": ["A00", "A01"],
                "quota": 90,
            },
            {
                "major_code": "7140231",
                "major_name": "Sư phạm Tiếng Anh",
                "year": 2024,
                "cutoff_score": 25.5,
                "subject_combinations": ["D01"],
                "quota": 110,
            },
            {
                "major_code": "7340101",
                "major_name": "Quản trị kinh doanh",
                "year": 2024,
                "cutoff_score": 21.0,
                "subject_combinations": ["A00", "A01", "D01"],
                "quota": 150,
            },
        ]

        # Search matching records
        results = [
            d
            for d in qnu_data
            if (major in d["major_name"].lower() or major in d["major_code"])
            and (d["year"] == year or not year)
        ]

        if not results:
            return {
                "found": False,
                "message": f"Không tìm thấy dữ liệu điểm chuẩn cho ngành '{parameters.get('major_name')}' năm {year}.",
                "hotline": "0256.3846.156",
            }

        return {
            "found": True,
            "total": len(results),
            "records": results,
            "hotline": "0256.3846.156",
        }
