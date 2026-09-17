"""Canonical document taxonomy imported from qnu-ai-core.

The catalog is deliberately transport-independent.  Database rows are the
runtime source of truth, while this immutable catalog is the versioned import
source used by the startup synchronizer and the explicit sync endpoint.
"""

from __future__ import annotations

import re
import unicodedata
from typing import TypedDict


class DocumentTypeDefinition(TypedDict):
    """One canonical document type definition."""

    code: str
    name: str
    category: str
    description: str
    priority: int
    retention_period: str


CATEGORY_NAMES: dict[str, str] = {
    "legal_internal": "Văn bản Quy phạm & Nội bộ",
    "administrative": "Văn bản Hành chính Điều hành",
    "academic": "Văn bản Đào tạo & Học thuật",
    "forms": "Biểu mẫu & Tiếp nhận",
}

ND30_CODES = frozenset(
    {
        "nghi_quyet",
        "quyet_dinh",
        "chi_thi",
        "quy_che",
        "quy_dinh",
        "thong_cao",
        "thong_bao",
        "huong_dan",
        "chuong_trinh",
        "ke_hoach",
        "phuong_an",
        "de_an",
        "du_an",
        "bao_cao",
        "bien_ban",
        "to_trinh",
        "hop_dong",
        "cong_van",
        "cong_dien",
        "ban_ghi_nho",
        "thoa_thuan_mou",
        "giay_uy_quyen",
        "giay_moi",
        "giay_gioi_thieu",
        "giay_nghi_phep",
        "phieu_gui",
        "phieu_chuyen",
        "phieu_bao",
    }
)

DOCUMENT_TYPE_CATALOG: tuple[DocumentTypeDefinition, ...] = (
    {
        "code": "quy_che",
        "name": "Quy chế",
        "category": "legal_internal",
        "description": "Văn bản quy định toàn diện về một lĩnh vực công tác, tổ chức hoặc đào tạo (VD: Quy chế Đào tạo, Quy chế Học vụ, Quy chế Tuyển sinh).",
        "priority": 10,
        "retention_period": "Vĩnh viễn",
    },
    {
        "code": "quy_dinh",
        "name": "Quy định",
        "category": "legal_internal",
        "description": "Văn bản cụ thể hóa các chế độ, chính sách hoặc quy tắc thực hiện nhiệm vụ trong toàn trường.",
        "priority": 9,
        "retention_period": "Vĩnh viễn",
    },
    {
        "code": "quyet_dinh",
        "name": "Quyết định",
        "category": "legal_internal",
        "description": "Văn bản áp dụng pháp luật ban hành các chủ trương, phê duyệt kế hoạch, nhân sự hoặc ban hành quy chế.",
        "priority": 9,
        "retention_period": "Vĩnh viễn",
    },
    {
        "code": "nghi_quyet",
        "name": "Nghị quyết",
        "category": "legal_internal",
        "description": "Nghị quyết của Hội đồng trường hoặc Đảng ủy về phương hướng, chiến lược phát triển.",
        "priority": 9,
        "retention_period": "Vĩnh viễn",
    },
    {
        "code": "chi_thi",
        "name": "Chỉ thị",
        "category": "legal_internal",
        "description": "Văn bản chỉ đạo các đơn vị trực thuộc triển khai nhiệm vụ trọng tâm cấp bách.",
        "priority": 8,
        "retention_period": "10 năm",
    },
    {
        "code": "thong_cao",
        "name": "Thông cáo",
        "category": "legal_internal",
        "description": "Thông cáo chính thức của Nhà trường về chủ trương, sự kiện quan trọng (theo NĐ 30/2020/NĐ-CP).",
        "priority": 8,
        "retention_period": "Vĩnh viễn",
    },
    {
        "code": "thong_bao",
        "name": "Thông báo",
        "category": "administrative",
        "description": "Văn bản truyền đạt thông tin, lịch trình công tác, hướng dẫn thực hiện cho cán bộ và người học.",
        "priority": 6,
        "retention_period": "5 năm",
    },
    {
        "code": "ke_hoach",
        "name": "Kế hoạch",
        "category": "administrative",
        "description": "Kế hoạch năm học, kế hoạch tuyển sinh, kế hoạch công tác khoa học hoặc hoạt động đoàn thể.",
        "priority": 7,
        "retention_period": "10 năm",
    },
    {
        "code": "de_an",
        "name": "Đề án",
        "category": "administrative",
        "description": "Đề án tuyển sinh trình độ đại học/sau đại học, đề án mở ngành mới, đề án chuyển đổi số.",
        "priority": 8,
        "retention_period": "Vĩnh viễn",
    },
    {
        "code": "phuong_an",
        "name": "Phương án",
        "category": "administrative",
        "description": "Phương án tổ chức thi, phương án xét tuyển, phương án tài chính và cơ sở vật chất.",
        "priority": 7,
        "retention_period": "5 năm",
    },
    {
        "code": "chuong_trinh",
        "name": "Chương trình",
        "category": "administrative",
        "description": "Chương trình công tác trọng tâm, chương trình hành động hoặc chương trình sự kiện.",
        "priority": 7,
        "retention_period": "5 năm",
    },
    {
        "code": "huong_dan",
        "name": "Hướng dẫn",
        "category": "administrative",
        "description": "Văn bản hướng dẫn quy trình, hồ sơ thủ tục, thao tác nghiệp vụ trên các hệ thống số.",
        "priority": 8,
        "retention_period": "5 năm",
    },
    {
        "code": "cong_van",
        "name": "Công văn",
        "category": "administrative",
        "description": "Văn bản trao đổi công việc, đề nghị phối hợp, phúc đáp giữa nhà trường với cơ quan ngoài và giữa các phòng ban.",
        "priority": 6,
        "retention_period": "5 năm",
    },
    {
        "code": "to_trinh",
        "name": "Tờ trình",
        "category": "administrative",
        "description": "Văn bản trình cấp trên xem xét, phê duyệt một đề xuất, dự thảo hoặc dự toán kinh phí.",
        "priority": 7,
        "retention_period": "10 năm",
    },
    {
        "code": "bao_cao",
        "name": "Báo cáo",
        "category": "administrative",
        "description": "Báo cáo tổng kết năm học, báo cáo 3 công khai, báo cáo kiểm định chất lượng, báo cáo tài chính.",
        "priority": 7,
        "retention_period": "10 năm",
    },
    {
        "code": "bien_ban",
        "name": "Biên bản",
        "category": "administrative",
        "description": "Biên bản họp Hội đồng, biên bản nghiệm thu đề tài khoa học, biên bản bàn giao.",
        "priority": 6,
        "retention_period": "10 năm",
    },
    {
        "code": "thoa_thuan_mou",
        "name": "Bản Thỏa thuận / MOU",
        "category": "administrative",
        "description": "Bản ghi nhớ hợp tác (MOU/MOA) với doanh nghiệp, trường đại học đối tác trong và ngoài nước.",
        "priority": 7,
        "retention_period": "Vĩnh viễn",
    },
    {
        "code": "hop_dong",
        "name": "Hợp đồng",
        "category": "administrative",
        "description": "Hợp đồng nghiên cứu khoa học, hợp đồng đào tạo, hợp đồng dịch vụ kỹ thuật.",
        "priority": 8,
        "retention_period": "10 năm",
    },
    {
        "code": "cong_dien",
        "name": "Công điện",
        "category": "administrative",
        "description": "Công điện chỉ đạo khẩn, đôn đốc nhiệm vụ cấp bách qua hệ thống thông tin (theo NĐ 30/2020/NĐ-CP).",
        "priority": 9,
        "retention_period": "10 năm",
    },
    {
        "code": "ban_ghi_nho",
        "name": "Bản Ghi nhớ",
        "category": "administrative",
        "description": "Bản ghi nhớ công tác, ghi nhận nội dung trao đổi, làm việc (theo NĐ 30/2020/NĐ-CP).",
        "priority": 6,
        "retention_period": "10 năm",
    },
    {
        "code": "du_an",
        "name": "Dự án",
        "category": "administrative",
        "description": "Dự án đầu tư, nhiệm vụ KHCN, dự án chuyển đổi số có mục tiêu, kinh phí, tiến độ (theo NĐ 30/2020/NĐ-CP; khác Đề án).",
        "priority": 7,
        "retention_period": "10 năm",
    },
    {
        "code": "giao_trinh",
        "name": "Giáo trình",
        "category": "academic",
        "description": "Giáo trình chính thức của các ngành học do Trường Đại học Quy Nhơn thẩm định và xuất bản.",
        "priority": 9,
        "retention_period": "Vĩnh viễn",
    },
    {
        "code": "bai_giang",
        "name": "Bài giảng / Slide",
        "category": "academic",
        "description": "Tập bài giảng điện tử, tài liệu học tập của giảng viên phục vụ sinh viên các hệ đào tạo.",
        "priority": 8,
        "retention_period": "5 năm",
    },
    {
        "code": "de_cuong_mon_hoc",
        "name": "Đề cương Chi tiết Học phần",
        "category": "academic",
        "description": "Đề cương chi tiết quy định chuẩn đầu ra, số tín chỉ, nội dung và hình thức đánh giá học phần.",
        "priority": 9,
        "retention_period": "10 năm",
    },
    {
        "code": "de_tai_nckh",
        "name": "Đề tài NCKH",
        "category": "academic",
        "description": "Thuyết minh đề tài, báo cáo tổng kết đề tài NCKH các cấp (cơ sở, tỉnh, bộ, NAFOSTED).",
        "priority": 8,
        "retention_period": "Vĩnh viễn",
    },
    {
        "code": "bai_bao_khoa_hoc",
        "name": "Bài báo Khoa học / Scopus",
        "category": "academic",
        "description": "Bài báo công bố trên các tạp chí khoa học quốc tế Scopus/WoS và tạp chí chuyên ngành trong nước.",
        "priority": 8,
        "retention_period": "Vĩnh viễn",
    },
    {
        "code": "ky_yeu_hoi_thao",
        "name": "Kỷ yếu Hội thảo",
        "category": "academic",
        "description": "Kỷ yếu các hội thảo, hội nghị khoa học quốc gia và quốc tế do trường chủ trì.",
        "priority": 7,
        "retention_period": "Vĩnh viễn",
    },
    {
        "code": "bieu_mau_hanh_chinh",
        "name": "Biểu mẫu Hành chính",
        "category": "forms",
        "description": "Các mẫu phiếu, biểu bảng, phiếu đánh giá KPI, thanh toán công tác dành cho cán bộ giảng viên.",
        "priority": 8,
        "retention_period": "5 năm",
    },
    {
        "code": "don_tu_sinh_vien",
        "name": "Đơn từ & Thủ tục Sinh viên",
        "category": "forms",
        "description": "Mẫu đơn xin nghỉ học tạm thời, đơn xin miễn giảm học phí, đơn xin chuyển ngành, đơn phúc khảo.",
        "priority": 8,
        "retention_period": "5 năm",
    },
    {
        "code": "phieu_khao_sat",
        "name": "Phiếu Khảo sát / Đánh giá",
        "category": "forms",
        "description": "Mẫu phiếu lấy ý kiến người học về hoạt động giảng dạy, khảo sát cựu sinh viên và doanh nghiệp.",
        "priority": 6,
        "retention_period": "3 năm",
    },
    {
        "code": "giay_uy_quyen",
        "name": "Giấy Ủy quyền",
        "category": "forms",
        "description": "Giấy ủy quyền thực hiện nhiệm vụ, ký thay theo phân cấp (theo NĐ 30/2020/NĐ-CP).",
        "priority": 6,
        "retention_period": "5 năm",
    },
    {
        "code": "giay_moi",
        "name": "Giấy Mời",
        "category": "forms",
        "description": "Giấy mời họp, hội thảo, sự kiện của Nhà trường (theo NĐ 30/2020/NĐ-CP).",
        "priority": 7,
        "retention_period": "5 năm",
    },
    {
        "code": "giay_gioi_thieu",
        "name": "Giấy Giới thiệu",
        "category": "forms",
        "description": "Giấy giới thiệu cán bộ, sinh viên liên hệ công tác (theo NĐ 30/2020/NĐ-CP).",
        "priority": 6,
        "retention_period": "5 năm",
    },
    {
        "code": "giay_nghi_phep",
        "name": "Giấy Nghỉ phép",
        "category": "forms",
        "description": "Giấy đề nghị nghỉ phép năm, nghỉ việc riêng của viên chức, người lao động (theo NĐ 30/2020/NĐ-CP).",
        "priority": 5,
        "retention_period": "5 năm",
    },
    {
        "code": "phieu_gui",
        "name": "Phiếu Gửi",
        "category": "forms",
        "description": "Phiếu gửi tài liệu, hồ sơ kèm theo khi chuyển văn bản (theo NĐ 30/2020/NĐ-CP).",
        "priority": 5,
        "retention_period": "5 năm",
    },
    {
        "code": "phieu_chuyen",
        "name": "Phiếu Chuyển",
        "category": "forms",
        "description": "Phiếu chuyển văn bản đến đơn vị xử lý, ghi ý kiến chỉ đạo (theo NĐ 30/2020/NĐ-CP).",
        "priority": 5,
        "retention_period": "5 năm",
    },
    {
        "code": "phieu_bao",
        "name": "Phiếu Báo",
        "category": "forms",
        "description": "Phiếu báo phát văn bản, báo nhận tài liệu (theo NĐ 30/2020/NĐ-CP).",
        "priority": 5,
        "retention_period": "5 năm",
    },
)

DOCUMENT_TYPE_CODES: tuple[str, ...] = tuple(item["code"] for item in DOCUMENT_TYPE_CATALOG)

_CATALOG_BY_CODE = {item["code"]: item for item in DOCUMENT_TYPE_CATALOG}
_CATALOG_BY_NAME = {unicodedata.normalize("NFC", item["name"]).casefold(): item["code"] for item in DOCUMENT_TYPE_CATALOG}
_LEGACY_ALIASES = {
    "decision": "quyet_dinh",
    "submission": "to_trinh",
    "notice": "thong_bao",
    "official_dispatch": "cong_van",
    "general_draft": "thong_bao",
    "nghi dinh": "quy_dinh",
    "ma tran de thi": "de_cuong_mon_hoc",
}


def _normalize_lookup(value: str) -> str:
    normalized = unicodedata.normalize("NFC", value).strip().casefold()
    return re.sub(r"\s+", " ", normalized.replace("-", " "))


def normalize_document_type_code(value: str | None) -> str | None:
    """Normalize canonical codes and legacy display/engine values."""
    if value is None or not value.strip():
        return None
    lookup = _normalize_lookup(value)
    if lookup in _CATALOG_BY_CODE:
        return lookup
    if lookup in _CATALOG_BY_NAME:
        return _CATALOG_BY_NAME[lookup]
    return _LEGACY_ALIASES.get(lookup)


def get_document_type_label(code: str | None) -> str | None:
    """Return the official display name for a canonical code."""
    if not code:
        return None
    definition = _CATALOG_BY_CODE.get(code)
    return definition["name"] if definition else None


def document_type_source_hash() -> str:
    """Return a stable hash of the source catalog for sync auditing."""
    import hashlib
    import json

    payload = json.dumps(DOCUMENT_TYPE_CATALOG, ensure_ascii=False, sort_keys=True)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()
