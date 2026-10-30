# Phiên 737 — Sửa DOCX mẫu của bộ kiểm thử backend

Ngày: 2026-10-30. Người dùng yêu cầu sửa lỗi DOCX còn lại sau khi E2E đạt 14/14 chặng.

## Căn cứ

- Tái hiện đúng ID lỗi: `tests/integration/test_auto_extraction_710.py::test_docx_table_has_real_structure_and_original_is_unchanged`, FAIL với Gotenberg HTTP 500. Lần tái hiện dùng DB test riêng và Gotenberg của project E2E, không sửa endpoint cấu hình đang phục vụ.
- `tests/integration/ocr_support.py::docx_with_table` tạo ZIP có document/footnotes XML nhưng thiếu officeDocument relationship, content type cho document, styles và liên kết footnotes. Parser XML nội bộ đọc được không có nghĩa đây là Word package hợp lệ cho LibreOffice.
- Sau sửa package, test auto DOCX đã PASS với nguyên các assertion về bảng, span, chữ, footnote và bytes gốc. Test OCR DOCX lộ thêm assertion cũ buộc `docx-story` trong khi runtime được ghim `gotenberg-libreoffice`; không phải lỗi chuyển đổi mới.

## Thay đổi

- `backendV1/tests/docx_fixture.py`: fixture độc lập DB, OPC content types/root relationship, document relationships/styles/footnotes hợp lệ; table grid/borders và page section rõ ràng. Giữ header hai tầng, row/col span, ô rỗng, `0`, `-`, hai năm và chú thích.
- `backendV1/tests/integration/ocr_support.py`: dùng lại fixture qua public helper hiện có. Các helper OCR và TABLE_RESPONSE giữ nguyên; không thêm điều kiện đặc biệt cho một câu test.
- `backendV1/tests/integration/test_ocr_processing_api.py`: kiểm converter thực tế đúng cấu hình đã chọn trước khi tạo run, thay vì ép Story cũ. Không nới assertion dữ liệu/schema.
- `backendV1/tests/unit/test_docx_fixture_737.py`: kiểm registration/relationships/footnote references và literal/merge/header trước khi cần DB hoặc converter.
- File test OCR cũ có CRLF ở HEAD, đã xác minh và chuẩn hóa LF theo quy chuẩn. So sánh bỏ khác biệt EOL chỉ có import, chụp expected converter và assertion tương ứng (3 dòng thêm/1 dòng bỏ).
- Không sửa mã ứng dụng, cấu hình DB phục vụ, parser, model/provider hay cơ chế fallback. Giữ diff các phiên 733–736.

## Kiểm chứng thực chạy

| Kiểm tra | Kết quả |
| --- | --- |
| Tái hiện DOCX auto trước sửa | FAIL: 1 test, HTTP500, 5.05s |
| Unit package/HTML DOCX + renderer recovery/contract | PASS: 18 test, 2.08s |
| Auto extraction710 + OCR API + observability644 + fixture737 + renderer714/715 | PASS: 46 test, 84.18s, exit0 |
| LibreOffice thực tế qua HTTP | 200, PDF1trang, có chữ tiếng Việt và footnote |
| Ruff check bốn file | PASS |

Đã xem ảnh PDF render tại `tmp/docx-737-render.png`: bảng, ô gộp và footnote hiển thị đúng. Integration kiểm lại bảng parsed, giá trị literal, cấu trúc và giữ bytes nguồn. Các model OCR trong regression là loopback, không gọi QNU inference thật.

DB test `qnu_v1_test_docx_737_*` tạo mới, local storage riêng, cache/queue namespace riêng; DB được dọn sau subprocess. Không truncate DB của phiên E2E. Log trong `tmp/docx-737-before.log`, `tmp/docx-737-regression-final.log`; full gate ghi riêng ở `tmp/docx-737-full.log` và được cập nhật khi kết thúc.

## Kết quả gate tổng thể

**FAIL, chưa thể báo toàn bộ backend đạt.** Lượt đầu `pytest -v -x` thu thập 907 ca, đạt 188, skip 1 và dừng vì `TEST_REDIS_URL` chưa có ở ca gateway. Đã bổ sung biến này trong tiến trình test tạm, dùng các Redis DB thử rỗng riêng (khác DB0 của E2E), không ghi `.env` hoặc đổi cấu hình phục vụ.

Đối chiếu toàn bộ 907 node ID; giữ 188 ca đã PASS, chia 719 ca còn lại vào ba DB PostgreSQL/cache namespace/Redis DB độc lập. Ca gateway thiếu biến đã chạy lại PASS. Các nhóm dùng `-x` nên dừng ở lỗi đầu của nhóm; **tổng hợp duy nhất: 410 PASS, 2 FAIL, 1 ERROR setup, 494 NOT RUN**. Không cộng trùng skip/lỗi thiết lập cũ vào kết quả đã phục hồi.

Các lỗi ngoài DOCX còn lại:

- `tests/integration/test_lifecycle_659.py::test_preview_is_bound_to_actor_and_state`: accept delete trả404, expected200. Test dùng source PDF, không gọi fixture DOCX.
- `tests/integration/test_source_purge_716.py::test_unpublished_purge_is_durable_irreversible_and_keeps_other_uploads`: GET source-deletions trả422, expected danh sách rỗng.
- `tests/integration/test_recovery_666.py::test_recovery_rejects_serving_target_wrong_confirmation_and_non_admin`: fixture thư mục tạm lỗi `WinError5` tại thư mục pytest của Windows.

Chưa sửa hành vi lifecycle/purge/quyền hoặc ACL máy trong phạm vi DOCX này. Ba subprocess exit1 và đã dọn DB test; không để test chạy nền. Bằng chứng: `tmp/docx-737-shard-{0,1,2}.log`, `tmp/docx-737-full-summary.json` (kiểm tổng PASS/FAIL/ERROR/NOT RUN bằng đúng907 ID).

Unit native extraction710 kiểm riêng cũng PASS14 ca. Các ca DOCX đã sửa đều đạt trong regression và lượt rộng. Ruff check/format theo phạm vi, UTF-8 không BOM/LF, liên kết mới và diff-check được kiểm cuối task.

Trong lúc tách fixture có một lượt collection lỗi import; đã sửa ngay, không coi lượt lỗi này là PASS. 46 regression cuối chạy sau batch ổn định.

## Trạng thái E2E và giới hạn

- Đã đọc checkpoint/báo cáo người dùng sau phiên 736: chat, permissions, lifecycle đều PASS, không skipped/flaky; phiên `7f9361961005` đạt 14/14. Đây là kết quả E2E đã chạy trước task này, không phải chạy lại ở phiên 737.
- Phiên 737 không restart API/worker, không upload/xóa tài liệu của người dùng và không chạy lại lifecycle. Lỗi sửa ở fixture backend riêng nên không cần làm lại E2E đã đạt.
- Bằng chứng converter200 và regression không thay thế benchmark mọi loại DOCX; không kết luận bộ backend tổng thể PASS nếu full gate chưa đạt.
