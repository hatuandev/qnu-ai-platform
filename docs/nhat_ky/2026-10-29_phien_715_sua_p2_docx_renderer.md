# Context715 — Xử lý các P2 DOCX renderer

Ngày: 2026-10-29. Yêu cầu: tiếp tục các P2 từ review713 sau sửa P1 ở714. Giữ yêu cầu không chạy test, không restart dịch vụ.

## Thay đổi theo finding

- F03 (HTTP giữ khóa render): `render_async` thực hiện Gotenberg conversion trong worker thread trước khi lấy `_render_lock`. Sau khi có PDF, helper `_render_converted_docx` rasterise dưới khóa chung. PDF trực tiếp, Story và saved PDF vẫn giữ khóa cho thao tác MuPDF. Hàm đồng bộ render_document dùng cùng helper để giữ nhất quán metadata/bytes/warnings; runtime tiếp tục đi qua async boundary hiện có. Không thay fingerprint hay profile đã ghim ở714.
- F04 (raw error log):714 đã loại bỏ logging response body. Batch này thêm sự kiện có cấu trúc qua logger hiện có, chỉ ghi event/status_code hoặc error_type. Không đọc response.text khi lỗi, không ghi URL/payload/exception message. Exception chuyển đổi từ HTTP được raise from None để traceback mặc định không in nguyên nhân transport có thể chứa thông tin nhạy cảm. Không mất machine code và thông báo lỗi đã lọc; không thêm fallback.
- F05 (unit test gọi dịch vụ thật): thêm fixture opt-in offline_document_conversion vào unit/conftest.py. Ba module test render/native/P2 sử dụng fixture; httpx.Client/AsyncClient mặc định bị chặn và ca Gotenberg phải ghi đè bằng fake cụ thể. Fixture không autouse toàn bộ unit suite, không ảnh hưởng các bài kiểm tra provider/HTTP khác. Các ca cache714 đã mock đường gọi converter từ trước.
- Hướng dẫn38 bổ sung ranh giới khóa, log và isolation. Không sửa FE, API/schema/migration, ModelOps, env hoặc hạ tầng.

## Regression đã viết, chưa chạy

Tệp mới test_docx_renderer_p2_715.py có6ca:

1. DOCX đang chờ fake Gotenberg nhưng PDF vẫn render xong; bước rasterise DOCX/PDF phải giữ khóa.
2. Conversion lỗi không vào vùng MuPDF và không gọi rasterise.
3. HTTP503 chỉ ghi status, thuộc tính text của error response không được đọc.
4. Transport error chỉ ghi loại lỗi; formatted traceback không chứa chuỗi nhạy cảm của fake exception.
5. Chọn Story không dựng HTTP client hoặc gọi Gotenberg.
6. Fixture từ chối HTTP client không được mock, cả sync và async.

Đây là mã regression chưa thực thi, không báo PASS cho các hành vi trên.

## Kiểm tra tĩnh thực hiện

Từ root repo:

- `uv run --project backendV1 --frozen --extra dev --no-sync ruff format <5 tệp Python trong phạm vi>`: exit0.
- `uv run --project backendV1 --frozen --extra dev --no-sync ruff check <5 tệp Python trong phạm vi>`: PASS exit0.
- Python ast.parse/UTF-8 noBOM/LF trên5file: PASS exit0; không import application hoặc test modules.
- `git diff --check` theo file trong phạm vi: PASS exit0.
- TEST/full suite/runtime/benchmark/liveGotenberg/API/DB/model: NOT RUN theo yêu cầu. Không đo latency nên không tuyên bố tăng thông lượng/hiệu năng đã được chứng minh.

## Bàn giao

Ba P2 đã xử lý ở mã trong phạm vi review713; các bất biến P1 được giữ. Cần chạy lại phiên v1-dev để nhận mã mới, nhưng agent không tự restart. Không thay renderer revision vì chỉ đổi scheduling và logging, không chủ đích đổi bytes kết xuất. Không reprocess, migrate, index, đổi publication hoặc push. Giữ toàn bộ diff đồng thời của người dùng và lịch sử714/713. Chưa có xác nhận runtime cho batch này.
