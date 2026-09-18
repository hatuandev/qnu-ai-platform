# Nhật Ký Phiên Làm Việc #90: Góp Ý Định Hướng Chức Năng Trọng Tâm

- **Thời gian:** 2026-09-18 16:50 (UTC+7)
- **Người thực hiện:** AI Senior Full-Stack Architect & Enterprise AI Systems Specialist
- **Mục tiêu:** Chuyển phần tư vấn chiến lược sản phẩm thành tài liệu chính thức để làm căn cứ rà soát roadmap QNU AI Platform.

## Thay Đổi Chính

| Tệp | Hành động | Mô tả |
| :--- | :--- | :--- |
| `docs/gop_y_dinh_huong_chuc_nang_trong_tam_qnu_ai_platform_2026-09-18.md` | Tạo mới | Định hướng sản phẩm, thứ tự P0–P3, Golden Assistant Quy chế, phân bổ nguồn lực, roadmap và production acceptance gate |
| `docs/memory/PROJECT_CONTEXT.md` | Cập nhật | Ghi nhận phiên #90 và quyết định định hướng sản phẩm |
| `docs/memory/snapshots/2026-09-18_session_90.md` | Tạo mới | Lưu trạng thái phiên tài liệu |
| `docs/WORK_LOG.md` | Cập nhật | Bổ sung phiên #90 vào mục lục tiến trình |

## Quyết Định Chính

1. Năm trợ lý hiện tại là Official Starter Templates, không phải giới hạn cứng của nền tảng.
2. Năng lực cốt lõi là tạo, kiểm thử, xuất bản và vận hành trợ lý mới trên dữ liệu thật.
3. Ưu tiên P0 là RAG Data Integrity, Assistant Runtime Integrity và Golden Assistant Quy chế.
4. Workflow DAG chỉ nên dùng khi có quy trình nhiều bước hoặc hành động nghiệp vụ.
5. Auth/RBAC/Tenant, Evaluation và Observability là production gate bắt buộc.

## Kiểm Chứng

- Tài liệu được lưu UTF-8 tiếng Việt sạch.
- Markdown links và whitespace được kiểm tra.
- Không thay đổi mã nguồn, schema hoặc quy trình runtime; không cần chạy lại test Backend/Frontend.
