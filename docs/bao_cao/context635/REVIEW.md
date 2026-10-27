# Context635 — Bỏ thư viện sửa chính tả hậu OCR

Người dùng xác nhận: “Bỏ thư viện, chỉ dùng kết quả Nemotron”. Đã gỡ thử nghiệm `vi-clean-text-normalizer`, dependency Git, bộ từ điển/ngram và các hook hậu OCR vừa thêm. Kiểm tra metadata môi trường Python xác nhận gói không còn cài; không còn tham chiếu thư viện hoặc hook trong app, pyproject và lockfile.

Thử nghiệm ngoại tuyến trước khi gỡ đã phát hiện thư viện có thể đổi “năm 2026” thành “nằm 2026”. Kết quả thử đó không được coi là bằng chứng OCR đúng. Không chạy thư viện này trên nguồn nghiệp vụ qua API/worker và không backfill tài liệu cũ.

Ngoài phần thử nghiệm, cleaner cũ có ba phép thay từ: “số chỉ …” → “chỉ số …”, “kí kết” → “ký kết”, “kí hợp đồng” → “ký hợp đồng”. Đã bỏ các phép thay này để chữ OCR không bị sửa bằng quy tắc chính tả cục bộ. Vẫn giữ xử lý cấu trúc/định dạng bảng, nối trang và bằng chứng raw để đối chiếu. Điều này không khẳng định Nemotron luôn nhận dạng đúng chính tả.

Extraction fingerprint đổi từ `layout-v24-ocr-table-evidence` sang `layout-v25-ocr-literal-words` cho lần parse mới. Không tự chạy lại hoặc đổi các revision đã lưu. Sáu file trong source seal Context634 khớp nguyên hash; file source_extraction.py chỉ khác đúng version literal, đã xác minh bằng hash sau khi thay ngược chuỗi version trong bộ nhớ. Các sửa truyền engine, HTML → GFM và lưu raw OCR Office của Context634 được giữ.

## Kiểm chứng thực chạy

- Hai regression mới tái hiện trước sửa: **2 FAIL**, do các quy tắc thay từ cũ; sau sửa nằm trong bộ focused đạt dưới đây.
- Focused: **128 PASS, 23 subtest PASS**, 55,04 giây, exit0. Cwd `backend`; `.venv\Scripts\python.exe -m pytest tests/test_ocr_literal_635.py tests/test_ocr_cleaner.py tests/test_ocr_ingestion_634.py tests/test_nemotron_ocr_631.py tests/test_source_layout_extraction.py tests/test_ingestion_mixed_regressions.py tests/test_qnu_docx_markdown.py -q --tb=short --basetemp=storage/context635/pytest-removed-final -o faulthandler_timeout=30`.
- Ruff: **PASS**, exit0, đúng bốn file cleaner.py, source_extraction.py, test_ocr_cleaner.py, test_ocr_literal_635.py.
- Gỡ package, file hook, từ điển: **PASS**, exit0; dependency tiktoken của công việc trước vẫn được giữ. Không reset các diff khác.
- API đang chạy: `/openapi.json` **HTTP200**, OCRExtractResponse/OCRPageResult không còn trường `post_correction`. `/health/ready` **HTTP503**.
- Full gate sau gỡ: harness `storage/context635/run_isolated_tests.py` **exit1 trước khi pytest chạy**, PostgreSQL từ chối kết nối. Docker engine pipe không tồn tại, không có listener5432/6379 và không có ARQ worker tại thời điểm kiểm tra. Vì vậy **full Pytest NOT RUN**, không có pass/fail/skip mới để so baseline. Không tự bật lại Docker hoặc worker trong bước gỡ này; chưa xác minh end-to-end lại sau thay đổi cuối.

Lượt full trước khi người dùng chọn gỡ bị gián đoạn và không được tính nghiệm thu. Database test sở hữu riêng `qnu_test_context635_ebb1fc4973b6` đã được kiểm tra namespace/runtime rồi xóa đúng database đó; receipt `backend/storage/context635/removed-test-db.json`. Lượt thử full sau gỡ dừng ở kết nối, chưa tạo database mới. Bằng chứng máy đọc tại `backend/storage/context635/removal-verification.json`; các artifact local này được Git ignore.

Không đổi provider/defaults ModelOps, không đọc hoặc ghi lại key, không publish/index/Compiler. Các artifact cũ giữ nguyên; khi khởi động hạ tầng và worker trở lại, tiến trình mới sẽ nạp code hiện tại. Kết quả full Context634 là lịch sử, không thay cho full gate Context635.

[Kết quả gọn](result.json).
