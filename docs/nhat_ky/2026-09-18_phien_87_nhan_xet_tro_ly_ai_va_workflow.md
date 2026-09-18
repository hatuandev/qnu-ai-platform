# NHẬT KÝ LÀM VIỆC — PHIÊN #87
# Ngày: 2026-09-18 | Phiên Làm Việc: Đánh Giá Trợ Lý AI và Quy Trình Workflow

---

## 1. Mục Tiêu & Phạm Vi

- Đánh giá chức năng Trợ lý AI và quy trình Workflow như một chuỗi thực thi thống nhất.
- Đối chiếu cấu hình 7 lớp của Trợ lý với hành vi runtime thật.
- Rà soát Workflow Control Plane, compiler, DAG engine, versioning, checkpoint, approval, tools, RAG, ModelOps, citation và TM-08.
- Đánh giá riêng năm workflow Tuyển sinh, Quy chế, Thư viện, Soạn thảo và Ngân hàng câu hỏi.
- Tạo tài liệu nhận xét chi tiết trong thư mục `docs/` theo yêu cầu người dùng.
- Không sửa mã nguồn, cấu hình runtime hoặc các tệp ModelOps đang được phiên khác xử lý.

## 2. Kết Quả Chính

- Kết luận phân hệ ở mức **Internal Beta / Workflow Control Plane Preview**, điểm tổng hợp đề xuất **5.2/10**.
- UI và control plane đạt khoảng 7.0–8.0/10; runtime production chỉ khoảng 3.5–4.5/10.
- Xác định các rủi ro P0:
  - Chat tự đặt `is_approved=true`, làm bypass Human-in-the-loop.
  - Frontend LiveMode có fallback câu trả lời/citation/artifact giả khi Backend lỗi.
  - TM-08 dùng dữ liệu mô phỏng nhưng tham gia quality gate publish.
  - Execute/resume không khóa tuyệt đối vào immutable WorkflowVersion.
  - Tenant, người publish và người duyệt chưa đến từ trusted auth context.
  - Tool/export chưa enforce allowlist, permission và approval policy.
- Xác định khoảng cách cấu hình–runtime: primary/fallback model, retrieval policy, structured facts, tool allowlist, timeout, retry, permission, edge condition, checkpoint và data classification chưa được bind/enforce đầy đủ.
- Đề xuất gói ưu tiên **Assistant–Workflow Runtime Integrity** trước khi mở rộng thêm node hoặc UI.

## 3. Tệp Thay Đổi

| Tệp | Hành động | Mô tả |
| :--- | :--- | :--- |
| [`docs/nhan_xet_tro_ly_ai_va_workflow_2026-09-18.md`](../nhan_xet_tro_ly_ai_va_workflow_2026-09-18.md) | Tạo mới | Báo cáo scorecard, đánh giá 7 bước, năm workflow, rủi ro P0/P1/P2, kiến trúc mục tiêu, roadmap và production gate |
| [`docs/memory/PROJECT_CONTEXT.md`](../memory/PROJECT_CONTEXT.md) | Cập nhật | Ghi nhận kết luận phiên #87 và backlog Runtime Integrity |
| [`docs/memory/snapshots/2026-09-18_session_87.md`](../memory/snapshots/2026-09-18_session_87.md) | Tạo mới | Snapshot trạng thái sau phiên đánh giá |
| [`docs/WORK_LOG.md`](../WORK_LOG.md) | Cập nhật | Bổ sung phiên #87 vào nhật ký tổng hợp |

Không cập nhật `docs/quy_trinh/` vì phiên này chỉ đánh giá và lập tài liệu, không thay đổi luồng nghiệp vụ hoặc mã runtime.

## 4. Verification

- Rà soát mã nguồn Assistant, Workflow, RAG, ModelOps, Evaluation và Frontend: hoàn tất.
- Đối chiếu năm workflow JSON và các test Assistant/Workflow/Chat/DAG: hoàn tất.
- Kiểm tra Backend API tại port 8001: không kết nối được tại thời điểm rà soát; không tạo execution mới.
- Không chạy lại Ruff/Pytest/Lint/Typecheck/Build vì phiên này chỉ thay đổi Markdown và worktree đang có mã ModelOps từ phiên song song.
- UTF-8 strict decode và mojibake scan trên tài liệu phiên #87: **Pass**.
- Markdown links và whitespace trên các file thuộc phiên #87: **Pass**.

## 5. Ghi Chú An Toàn Worktree

- Giữ nguyên toàn bộ thay đổi Backend/Frontend ModelOps của phiên song song.
- Không gọi Chat API, publish/rollback workflow, approve execution hoặc seed dữ liệu.
- Không thay đổi Assistant, Workflow, Provider, collection hoặc Qdrant.

