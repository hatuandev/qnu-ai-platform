import os

# 1. Update docs/nhat_ky/README.md
readme_path = os.path.join('docs', 'nhat_ky', 'README.md')
with open(readme_path, 'r', encoding='utf-8') as f:
    lines = f.readlines()

new_session_row = (
    "| **2026-10-06** | "
    "[`2026-10-06_phien_278_tinh_gon_toan_dien_root_workspace_va_chuan_hoa_frontend2.md`]"
    "(./2026-10-06_phien_278_tinh_gon_toan_dien_root_workspace_va_chuan_hoa_frontend2.md) | "
    "Tinh Gọn Toàn Diện Root Workspace, Di Chuyển 13 Script Scratch & Chuẩn Hóa Frontend2 Port 3000 | "
    "Tinh gọn 54% thư mục gốc (từ 39 còn 18 tệp); di chuyển 13 script scratch vào `scratch/archive/`; "
    "di chuyển tài liệu mẫu vào `docs/tai_lieu/samples/`; xóa node_modules cũ giải phóng ~500MB đĩa; "
    "lưu trữ `legacy/frontend_v1_backup/`; chuẩn hóa `run.ps1` trỏ thẳng `frontend2` (Port 3000) |\n"
)

lines.insert(9, new_session_row)
with open(readme_path, 'w', encoding='utf-8') as f:
    f.writelines(lines)
print('Updated docs/nhat_ky/README.md')

# 2. Update docs/WORK_LOG.md
worklog_path = os.path.join('docs', 'WORK_LOG.md')
with open(worklog_path, 'r', encoding='utf-8') as f:
    wlines = f.readlines()

new_worklog_row = (
    "| **2026-10-06 15:55** | AI Senior Full-Stack Architect | "
    "Tinh Gọn Toàn Diện Root Workspace, Di Chuyển 13 Script Scratch & Chuẩn Hóa Frontend2 Port 3000: "
    "Gom 13 script scratch ở Root vào `scratch/archive/`; Gom 8 tài liệu mẫu (.docx, .html, .md) vào `docs/tai_lieu/samples/`; "
    "Thư mục gốc giảm từ 39 tệp xuống còn 18 tệp chuẩn mực; Xóa node_modules cũ của frontend giải phóng ~500MB đĩa; "
    "Lưu trữ frontend cũ vào `legacy/frontend_v1_backup/`; Cập nhật `run.ps1` trỏ thẳng `frontend2` (Port 3000) làm mặc định duy nhất; "
    "Điều tra lỗi phân quyền Windows trên `document_types` | "
    "**Workspace Streamlined 100% ✓**<br>Root Cleaned (39 -> 18) \\| Scratch Archived \\| Frontend2 Unified \\| run.ps1 Updated | "
    "[2026-10-06_phien_278_tinh_gon_toan_dien_root_workspace_va_chuan_hoa_frontend2.md]"
    "(./nhat_ky/2026-10-06_phien_278_tinh_gon_toan_dien_root_workspace_va_chuan_hoa_frontend2.md) |\n"
)

wlines.insert(9, new_worklog_row)
with open(worklog_path, 'w', encoding='utf-8') as f:
    f.writelines(wlines)
print('Updated docs/WORK_LOG.md')

# 3. Update docs/memory/PROJECT_CONTEXT.md
context_path = os.path.join('docs', 'memory', 'PROJECT_CONTEXT.md')
with open(context_path, 'r', encoding='utf-8') as f:
    context_text = f.read()

header_marker = "## 1. Thông Tin Phiên Gần Nhất\n\n"
new_context_entry = (
    "## 1. Thông Tin Phiên Gần Nhất\n\n"
    "- **Thời gian cập nhật**: 2026-10-06 15:55 (UTC+7)\n"
    "- **Phiên số**: #278 (Tinh Gọn Toàn Diện Root Workspace & Chuẩn Hóa Frontend2 Port 3000)\n"
    "- **Kết quả phiên #278**:\n"
    "  - **Root Workspace tinh gọn 54%**: Giảm từ 39 tệp/thư mục xuống còn 18 tệp. Gom 13 script `scratch_*.py` vào `scratch/archive/`, gom 8 tài liệu mẫu (.docx, .html, .md) vào `docs/tai_lieu/samples/`.\n"
    "  - **Chuẩn hóa Frontend2 độc tôn**: Xóa `node_modules` cũ giải phóng ~500MB đĩa, lưu trữ bản cũ vào `legacy/frontend_v1_backup/`, cập nhật `run.ps1` trỏ thẳng `frontend2` (Port 3000).\n"
    "  - **Xác định nguyên nhân quyền `document_types`**: Quyền sở hữu bị gán cho SYSTEM/root từ Docker trước đây. Đã hướng dẫn lệnh PowerShell Admin để cấp quyền.\n"
    "  - Báo cáo chi tiết: [`docs/nhat_ky/2026-10-06_phien_278_tinh_gon_toan_dien_root_workspace_va_chuan_hoa_frontend2.md`](./nhat_ky/2026-10-06_phien_278_tinh_gon_toan_dien_root_workspace_va_chuan_hoa_frontend2.md).\n"
    "- **Phiên trước #277**:\n"
    "  - Khắc Phục Triệt Để Bounding Boxes Scan Bị Loạn & Bảng Markdown Bị Dồn Thẻ `<br>` / Mất Header Trên Scan Studio (QD2139).\n"
    "  - Báo cáo chi tiết: [`docs/nhat_ky/2026-10-06_phien_277_khac_phuc_triet_de_vung_scan_loan_va_bang_markdown_bi_don_br.md`](./nhat_ky/2026-10-06_phien_277_khac_phuc_triet_de_vung_scan_loan_va_bang_markdown_bi_don_br.md).\n"
)

import re
pattern = r"## 1\. Thông Tin Phiên Gần Nhất\s*\n\n- \*\*Thời gian cập nhật\*\*: 2026-10-06 15:20.*?- \*\*Phiên trước #276\*\*:"
new_context_text = re.sub(pattern, new_context_entry + "- **Phiên trước #276**:", context_text, flags=re.DOTALL)
if new_context_text != context_text:
    with open(context_path, 'w', encoding='utf-8') as f:
        f.write(new_context_text)
    print('Updated docs/memory/PROJECT_CONTEXT.md')
