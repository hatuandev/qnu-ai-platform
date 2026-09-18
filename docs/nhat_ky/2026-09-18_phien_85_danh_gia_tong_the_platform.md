# NHẬT KÝ LÀM VIỆC — PHIÊN #85
# Ngày: 2026-09-18 | Phiên Làm Việc: Đánh Giá Tổng Thể QNU AI Platform

---

## 1. Mục Tiêu & Phạm Vi

- Rà soát toàn bộ Platform để xác định mức độ hoàn thiện thực tế.
- Đối chiếu giữa mã nguồn, API đang chạy, dữ liệu PostgreSQL, tài liệu tiến độ và kiến trúc tham khảo từ `qnu-ai-core`.
- Phân biệt ba mức: giao diện/cấu hình đã có, runtime đã tích hợp và production đã được kiểm chứng.
- Không sửa code ModelOps/Provider do phiên #84 đang phát triển song song trong phần lớn thời gian đánh giá.

## 2. Kết Quả Chính

- Xác định trạng thái phù hợp là **Internal Beta / Engineering Preview**, chưa production-ready.
- Điểm tổng thể đề xuất: **5.6/10**.
- Điểm mạnh chính: Knowledge/OCR, UI quản trị, Workflow Control Plane, kiến trúc module và test automation.
- Rủi ro chính:
  - Router chưa enforce authentication/RBAC/tenant isolation.
  - Evaluation/TM-08 đang dùng câu trả lời và context mô phỏng.
  - Frontend LiveMode còn business mock fallback.
  - RAG retrieval có thật nhưng answer synthesis chưa gọi LLM.
  - Assistant primary/fallback model và tool policy chưa điều khiển runtime đầy đủ.
  - Workflow execution/resume chưa khóa vào immutable version.
  - DAG runtime thiếu timeout, retry/backoff, cancellation, schema và permission.
  - Nhiều file từ 1.000 đến gần 3.000 dòng.
- Dữ liệu live cho thấy Admissions, Regulations và Library đang có 0 document/0 chunk.

## 3. Tệp Thay Đổi

| Tệp | Hành động | Mô tả |
| :--- | :--- | :--- |
| [`docs/nhan_xet_tong_the_qnu_ai_platform_2026-09-18.md`](../nhan_xet_tong_the_qnu_ai_platform_2026-09-18.md) | Tạo mới | Báo cáo đánh giá chi tiết, scorecard, rủi ro P0/P1, roadmap và production acceptance gate |
| [`docs/memory/PROJECT_CONTEXT.md`](../memory/PROJECT_CONTEXT.md) | Cập nhật | Đặt lại maturity status theo runtime thực tế và thêm backlog ưu tiên |
| [`docs/memory/snapshots/2026-09-18_session_85.md`](../memory/snapshots/2026-09-18_session_85.md) | Tạo mới | Snapshot phiên đánh giá #85 |
| [`docs/WORK_LOG.md`](../WORK_LOG.md) | Cập nhật | Bổ sung phiên #85 vào nhật ký tổng hợp |

Không cập nhật `docs/quy_trinh/` vì phiên này không thay đổi luồng nghiệp vụ hoặc kiến trúc runtime; chỉ đánh giá hiện trạng.

## 4. Verification

- Backend Ruff: `uv run ruff check .` — **Pass, 0 lỗi**.
- Backend Pytest: `uv run --extra dev pytest -q` — **172 passed, 17 warnings** trong 93.91 giây.
- Frontend Biome: `npm run lint` — **Pass, 93 files**.
- Frontend TypeScript: `npm run typecheck` — **Pass**.
- Frontend production build: chạy lại sau khi phiên #84 hoàn tất — **Pass trong 8.82 giây**; cảnh báo bundle JS 1.50 MB.
- Zero Mojibake: `python scripts/check_mojibake.py` — **231 files sạch**.
- Backend readiness: PostgreSQL và Redis connected.

## 5. Ghi Chú An Toàn Worktree

- Các file ModelOps, API client và tài liệu phiên #83/#84 đã có thay đổi từ phiên khác.
- Phiên #85 không sửa các file code đó.
- `uv run` từng tự cập nhật `backend/uv.lock`; file đã được xác nhận sạch trước phiên và đã được khôi phục riêng.
