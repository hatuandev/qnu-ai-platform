# Context714 — Sửa hai P1 của DOCX renderer

Ngày: 2026-10-29. Người dùng chọn sửa P1 từ review713. Giữ chỉ dẫn không chạy test; không restart hoặc thay cấu hình đang chạy.

## Thay đổi

1. `Settings` là nguồn cấu hình Gotenberg duy nhất. Job DOCX mới dùng `DOCX_CONVERTER` (mặc định gotenberg-libreoffice), endpoint `GOTENBERG_URL` từ `.env` đã chọn và `DOCX_RENDERER_REVISION` (mặc định qnu-docx/v2). Renderer không còn đọc os.environ riêng hoặc tự chọn converter theo trạng thái mạng.
2. Config/fingerprint DOCX mới gồm converter, endpoint, revision triển khai và phiên bản PyMuPDF. Profile được lưu trong run config và đọc lại khi worker chạy. Gotenberg lỗi trả docx_converter_unavailable/docx_conversion_failed thay vì chuyển sang Story. Chọn Story phải tường minh cho job mới.
3. Phục hồi DOCX: helper dùng chung cho auto extraction và OCR thủ công đọc render_pdf qua helper kiểm size/hash hiện có, rồi rasterise lại PDF đó; không gọi converter lần hai. Metadata renderer/warnings được lưu cùng artifact PDF và commit trước page artifacts. PDF đã có nhưng metadata cũ thiếu được đánh dấu legacy-saved/legacy_converter_metadata_unavailable, không giả phiên bản converter.
4. Nếu chưa có PDF và revision triển khai đã khác profile đã ghim, worker báo renderer_version_changed. Nếu PyMuPDF đã thay đổi, cả render mới/cache render đều dừng để tránh đổi ảnh/bbox của cùng job.
5. Config cũ không có profile renderer tiếp tục theo Story; nếu đã có PDF thì sử dụng chính PDF đó. Fingerprint và payload PDF trực tiếp giữ cấu trúc cũ để tránh vô tình tạo job OCR/chi phí mới cho PDF chỉ vì bổ sung profile DOCX.
6. Metadata Gotenberg không còn lấy phiên bản PyMuPDF làm phiên bản converter. Ghi riêng rasterizer_version và revision triển khai; phiên bản Gotenberg chưa đo được giữ null. Revision triển khai do quản trị đặt và phải đổi khi image/font/options converter thay đổi; không tuyên bố đã tự phát hiện phiên bản server.

Không ghi đè nguồn/ảnh/artifact cũ, không nới artifact_conflict/render_mismatch, không đổi grants/model/quota hay publication. Việc bỏ fallback đồng thời bỏ log raw response/exception của nhánh Gotenberg cũ. Vấn đề HTTP giữ khóa render(P2) chưa xử lý trong batch này.

## File

- Code: platform/config.py; ocr/config.py, service.py, artifacts/render.py, execution.py, automatic.py.
- Mẫu cấu hình: backendV1/.env.example; không sửa .env đang chạy.
- Tài liệu: backendV1/docs/ocr-processing.md và hướng dẫn38.
- Regression đã viết, CHƯA CHẠY:6ca mới về endpoint từ .env, identity converter/endpoint/revision/rasterizer, fingerprint PDF tương thích, Gotenberg lỗi không fallback, cache PDF không gọi converter, artifact hỏng không reconvert; điều chỉnh ca Gotenberg cũ để dùng config tường minh và kiểm URL.

## Kiểm tra thực hiện

Từ root repo:

- `uv run --project backendV1 --frozen --extra dev --no-sync ruff format <9 tệp Python trong phạm vi>`: exit0; chỉ định dạng file được sửa.
- `uv run --project backendV1 --frozen --extra dev --no-sync ruff check <9 tệp Python trong phạm vi>`: PASS exit0.
- Python ast.parse và kiểm bytes UTF-8/noBOM/LF trên9file: PASS exit0, không import ứng dụng hoặc thực thi test.
- `git diff --check` trên file code/test/example/docs trong phạm vi: PASS exit0.
- TEST/full suite/live API/DB/queue/converter/model: NOT RUN theo yêu cầu. Các regression mới không được gắn PASS. Không dùng lint hoặc AST làm bằng chứng runtime.

## Bàn giao

Hai P1 đã sửa ở mã, chưa xác minh runtime. Không có migration mới. Không restart API/worker/FE; phiên đang chạy chưa tự nhận mã mới, người dùng cần dừng/chạy lại phiên v1-dev khi muốn áp dụng. Không reprocess/reindex tài liệu cũ hoặc đổi bản đang xuất bản. Giữ diff đồng thời về workspace navigation, FE, runner/Compose và PDF endpoint của người dùng. Không commit/push.
