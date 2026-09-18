# Nhật Ký Phiên #95 — Hiệu Chỉnh Nhận Xét và Review Code

> **Thời gian:** 18/09/2026, 20:30 (UTC+7)  
> **Mục tiêu:** Điều chỉnh đánh giá cho phù hợp với mô hình mật khẩu đơn giản giai đoạn dev, đồng thời review code đang thay đổi mà không can thiệp session seed song song.

## Kết Quả

- Báo cáo [nhận xét sau cải thiện](../nhan_xet_sau_cai_thien_platform_2026-09-18.md) đã được cập nhật thành review có evidence và mức ưu tiên xử lý.
- Đã chốt rằng dự án **không cần RBAC/SSO phức tạp** lúc này. Cần một Dev Access Gate phía server để bảo vệ app khi chia sẻ môi trường và cung cấp actor tin cậy cho approval.
- Maturity chưa tăng khỏi **6,4/10, Internal Beta** vì worktree hiện có lỗi lint/test và các rủi ro integrity chưa được giải quyết.

## Phát Hiện Chính

| Mức độ | Phát hiện | Tác động |
| :--- | :--- | :--- |
| P0 | Library/Question Bank seed không có nguồn gốc/tệp gốc/evidence | Không thể gọi dữ liệu là official hoặc dùng làm căn cứ trả lời public |
| P0 | `KnowledgeService` định nghĩa trùng các method cleanup | Bản sau ghi đè bản cũ; xóa document có thể không xóa file gốc/vector nhất quán |
| P0 | Evaluation fallback từ ground truth | Runtime fail vẫn có thể đạt score cao, TM-08 không độc lập |
| P0 | Seeder Assistant overwrite config hiện hữu | Restart có thể làm mất cấu hình quản trị |
| P0 | Dense Qdrant thiếu lifecycle/tenant/revision filter | Có nguy cơ trả pending/ghost/cross-scope vector |
| P0 | Approval và Tool Gateway bypass | Side effect chưa được kiểm soát bằng policy/actor tin cậy |
| P0 | Citation Guard fallback giữ citation không đủ evidence | UI có thể hiển thị nguồn như thể câu trả lời đã được căn cứ |
| P1 | Question Bank đổi generation workflow thành consult workflow | Cần tách luồng tra cứu và tạo bản nháp có phê duyệt |

## Kiểm Thử

- Backend Ruff: **fail 7 lỗi tại snapshot đầu review**.
- Nhóm test Assistant/Evaluation/RAG/Knowledge/Workflow: **71 pass, 1 fail, 17 warnings tại snapshot đầu review**.
- Zero Mojibake: **267 tệp sạch**.
- Trong lúc review có session song song tiếp tục sửa backend (cache, workflow version, knowledge cleanup). Các quality gate trên cần chạy lại khi session đó kết thúc; không chạy chồng để tránh nhiễu kết quả. Không chạy frontend checks vì không có file frontend đổi trong snapshot đầu review.

## Tệp Đã Cập Nhật

- [Báo cáo review](../nhan_xet_sau_cai_thien_platform_2026-09-18.md)
- [Project context](../memory/PROJECT_CONTEXT.md)
- [Memory snapshot #95](../memory/snapshots/2026-09-18_session_95.md)
- [Work log](../WORK_LOG.md)

## Đồng Bộ Quy Trình

Không cập nhật `docs/quy_trinh/` vì phiên này không thay đổi runtime/data flow; chỉ thực hiện review và tài liệu hóa. Khi sửa Dev Access Gate hoặc state machine lifecycle, cần tạo/cập nhật quy trình tương ứng ngay trong phiên triển khai.
