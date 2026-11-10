# Phiên 921 — Markdown/JSON và Rà soát chính tả FE V2

## Yêu cầu và phạm vi

Triển khai hoàn chỉnh phần Markdown/JSON và luồng tự động soát chính tả, kèm trang riêng để xem và sửa các gợi ý trên toàn tài liệu trong FE V2, kết nối bền vững với `backendV1`.
- Backend: `backendV1/` (FastAPI, SQLAlchemy async, ARQ, ModelOps).
- Frontend: `frontendV2/` (React 19, TanStack Router/Query, Tailwind, Biome).
- Giữ nguyên các thay đổi chưa commit, không reset DB, không tự động publish, không restart dịch vụ.

## Thay đổi triển khai

1. **Backend V1 (`ocr/review` & ARQ)**:
   - Thêm `list_checks(db, run, version)` trong `backendV1/qnu/domains/ocr/review/detection.py` truy vấn lịch sử kiểm tra theo run và text version đã ghim.
   - Bổ sung endpoint `GET /workspaces/{w}/collections/{c}/sources/{s}/revisions/{r}/processing-runs/{run_id}/text-review/checks` trong `backendV1/qnu/domains/ocr/review/router.py`.
   - Thêm ARQ background task `spelling_check_job` trong `backendV1/qnu/workers/tasks/ocr.py`. Tự động kích hoạt khi OCR hoàn tất (`outcome.status == "completed"`) với job ID chống trùng `qnu:v1:spelling:{run_id}:0` và khóa chống trùng `auto:spl:{run.id}:0`. Không khóa việc đọc tài liệu hay soạn thảo bản nháp.
   - Đăng ký `spelling_check_job` trong `backendV1/qnu/workers/settings.py`.

2. **Frontend V2 API & Query Hooks (`src/api/ocr/`)**:
   - Khai báo đầy đủ DTO contracts: `TextUnit`, `ReviewDocument`, `TextChange`, `SaveReview`, `Suggestion`, `DetectionResponse`, `DetectRequest`.
   - Bổ sung request callers và TanStack Query hooks: `useTextReviewQuery`, `useTextReviewChecksQuery`, `useSaveTextReviewMutation`, `useDetectTextReviewMutation`.

3. **Markdown & JSON trên màn hình Studio (`knowledge.$sourceId.tsx`)**:
   - `MarkdownView` (`src/components/knowledge/markdown-view.tsx`): 2 chế độ con "Xem trước" (Preview) và "Mã nguồn" (Raw). Xem trước trình bày chuẩn heading, paragraph, list, blockquote, bảng biểu Markdown, chuyển mã dẫn chứng `[S1]`, `[ev_...]` thành badge gọn gàng. Mã nguồn giữ nguyên định dạng thô, kèm nút Sao chép và Tải `.md`.
   - `JsonStructureDialog` (`src/components/knowledge/json-structure-dialog.tsx`): Hộp thoại xem cấu trúc dữ liệu JSON từ backend, có tìm kiếm từ khóa, Sao chép JSON và Tải tệp `.json`.
   - Đưa "Xem cấu trúc JSON", "Tải tệp JSON" và liên kết "Rà soát chính tả" vào menu `⋯` của header, giữ thanh thao tác chính tối giản.
   - `SpellingStatusStrip` (`src/components/knowledge/spelling-status-strip.tsx`): Dải thông tin trạng thái ngắn đặt ngay phía trên canvas nội dung biên tập, hiển thị các trạng thái: Đang soát chính tả trong nền / Có N vị trí nghi sai + Xem gợi ý / Chưa phát hiện lỗi chính tả / Kiểm tra chưa hoàn tất.

4. **Trang chuyên biệt "Rà soát chính tả" (`knowledge.$sourceId_.review.tsx`)**:
   - Route độc lập: `/knowledge/$sourceId/review`.
   - Header: Nút `← Quay lại`, tên tài liệu (kèm tooltip), badge đếm số vị trí chưa duyệt, nút phụ `Đối chiếu tệp gốc`, nút chính `Lưu thay đổi`.
   - Bộ lọc: Chờ duyệt / Đã nhận / Bỏ qua / Cần dò (withheld).
   - Card kiểm tra chi tiết: Bôi màu từ nghi sai trong ngữ cảnh đầy đủ, so sánh trực quan `Nguyên văn → Đề xuất`, hiển thị lý do ngắn gọn.
   - Thao tác: Áp dụng / Bỏ qua / Sửa tay / Hoàn tác. Tự động chuyển sang gợi ý kế tiếp sau khi thao tác.
   - Bảng dock xem tệp gốc đối chiếu (DOCX/PDF) có thể bật/tắt để tra cứu trực tiếp.
   - Thuật toán thay thế tuần tự (`src/lib/spelling-replacement-helpers.ts`): Áp dụng các thay đổi trên cùng một đơn vị văn bản theo thứ tự offset giảm dần (phải sang trái), bảo đảm character offsets của các vị trí phía trước không bị xô lệch.
   - Lưu nguyên tử: Gửi `SaveReview` lên `POST .../text-review`, tạo `TextVersion` mới (version = n + 1), sau đó tự động tạo `PreparationIntent` mới với `text_version = n + 1` để biên dịch lại nội dung trong nền. Không ghi đè bản đang phục vụ.
   - Cảnh báo rời trang (`beforeunload`) khi có các quyết định chỉnh sửa chưa được lưu.

## Kiểm chứng thực chạy

- `node --test frontendV2/src/lib/spelling-replacement-helpers.test.ts`: **4/4 PASS**, kiểm chứng thay thế đơn lẻ, thay thế nhiều vị trí trên cùng chuỗi không xô lệch offset, phát hiện chuỗi không khớp và chuyển đổi quyết định thành TextChange.
- `node --test frontendV2/src/lib/*.test.ts`: **15/15 PASS** toàn bộ kiểm thử thư viện frontend.
- `uv run --project backendV1 pytest backendV1/tests/unit/test_ocr_context_review_801.py backendV1/tests/unit/test_worker_model_timeout_819.py`: **19/19 PASS** (0.31s + 3.16s).
- `npm --prefix frontendV2 run typecheck`: **0 errors**, TypeScript biên dịch sạch hoàn toàn.
- `npm --prefix frontendV2 run lint`: **0 errors**, Biome kiểm tra 172 tệp sạch hoàn toàn.
- `npm --prefix frontendV2 run build`: **0 errors**, Vite build production thành công trong 1.95s, sinh chunk `knowledge._sourceId_.review-D8gUpnP_.js` sạch.

