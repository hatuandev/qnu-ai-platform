# Phiên 922 — Sửa soát chính tả và tệp xuất ở FE V2

## Phạm vi

Xử lý các lỗi phát hiện khi rà mã `d0941c83` ở luồng chuẩn bị, xem và chỉnh sửa tài liệu. Dữ liệu gốc và bản đang phục vụ được giữ trong vòng đời hiện có. Phạm vi là `backendV1/` và `frontendV2/`.

## Thay đổi

- Worker lấy đúng người yêu cầu OCR để kiểm tra quyền. Tự soát toàn bộ đoạn văn và ô bảng theo nhóm, ghim phiên bản, hash nguồn và cấu hình model. Chỉ chia lại nhóm có lỗi ngân sách token xác định, giữ kết quả đã hoàn tất. Lượt soát dùng thời hạn chung của tác vụ model. Lượt cũ thiếu tổng số đoạn không được hiển thị là đã soát toàn bộ.
- Studio chọn đúng phiên bản văn bản sau OCR. Trang rà soát giữ bản xem PDF khi đổi gợi ý và dùng vị trí ký tự Unicode như backend. Lưu hiệu đính và yêu cầu chuẩn bị lại có khóa riêng. Nếu đã lưu mà bước chuẩn bị gặp lỗi, người dùng có thể gửi lại riêng bước đó.
- Tải Markdown và JSON nguyên byte do máy chủ cung cấp. Bản xem Markdown lấy nhãn trạng thái từ phiên bản đang xem, rút gọn mã dẫn chứng đã xác định. Chỉ mục nội dung của bản đang phục vụ tiếp tục theo vòng đời duyệt và phát hành hiện có.
- Bảng tác vụ dùng tiến độ phần đã đo và tránh chuyển tiếp chiều rộng khi đổi kích thước màn hình.

## Kiểm chứng

- `frontendV2`: `npm run lint` (174 tệp), `npm run build` (gồm TypeScript), `node --test tests/studio-browser.mjs` (15 đạt), `node --test (Get-ChildItem src/lib/*.test.ts).FullName` (16 đạt). Tất cả exit 0. Trình duyệt dùng API mô phỏng.
- `backendV1`: `uv run --no-sync ruff check` và `ruff format --check` trên 9 tệp Python sửa, exit 0. Từ root chạy `uv run --no-sync --project backendV1 python -m pytest backendV1/tests/unit/test_worker_model_timeout_819.py -q`, 2 đạt, exit 0.
- Từ root, `uv run --no-sync --project backendV1 python backendV1/scripts/run_isolated_tests.py` với `test_ocr_text_review_651.py` và `test_compiler_draft_retains_tables_citations_raw_and_single_delivery`: 26 đạt trên PostgreSQL cô lập và provider mô phỏng, exit 0. Ca compiler xác nhận nội dung JSON, ETag và chính sách cache.
- Full Pytest đã khởi chạy bằng harness cô lập và chưa có kết quả cuối tại thời điểm bàn giao. Riêng thay đổi cuối về thời hạn worker đã chạy lại hai ca nêu trên.
- Chưa gọi model thật, chưa thử trên dữ liệu ứng dụng. Không có migration mới. Worker/API cần nạp mã mới để nhận thay đổi. Lượt OCR cũ không tự chạy lại chỉ vì cập nhật code.

[Snapshot phiên 922](../memory/snapshots/2026-11-10_session_922.md) · [Hợp đồng luồng chính](../quy_trinh/47_hop_dong_luong_chinh_backend_v1.md)
