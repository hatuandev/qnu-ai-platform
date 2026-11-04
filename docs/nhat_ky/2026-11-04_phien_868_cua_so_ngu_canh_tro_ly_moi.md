# Phiên 868 — Cửa sổ ngữ cảnh của trợ lý mới

Form tạo trợ lý điền sẵn `context_window=1`. API dùng cùng mặc định khi POST thiếu
`rag_policy` hoặc thiếu trường `context_window` bên trong policy. Người dùng vẫn
có thể chọn `0–5`. Cập nhật không gửi policy tiếp tục dùng cấu hình đã lưu. API
hỏi đáp trực tiếp và snapshot cũ thiếu policy dùng giá trị tương thích `0`.

Thay đổi nằm trong schema và router `assistants` ở backend, cùng cấu hình mặc
định, form và API client `assistants` ở frontend. Đã cập nhật hợp đồng và quy
trình RAG. Thay đổi áp dụng lúc tạo, không cần migration hoặc lập lại chỉ mục.

## Kiểm chứng

- Từ root, `backendV1/.venv/Scripts/python.exe backendV1/scripts/run_isolated_tests.py tests/unit/test_rag_policy_metadata_672.py tests/integration/test_conversations_649.py -q` thoát 0. 57 ca đạt, gồm mặc định POST, policy chỉ khai báo một phần và giữ `0` khi cập nhật. Cơ sở dữ liệu thử nghiệm đã được dọn.
- Backend `ruff check` trên hai tệp trợ lý và hai tệp kiểm thử liên quan thoát 0.
- Từ `frontendV1`, `npm exec -- vitest run tests/v1-assistants.test.ts tests/v1-rag-contracts-674.test.ts` thoát 0 với 32 ca đạt. Biome trên bốn tệp sửa và `npm run build` gồm TypeScript đều thoát 0.
- `npm run lint` toàn frontend thoát 1 với 27 lỗi ngoài các tệp đã qua Biome. `make.ps1 test-be` với `PYTEST_ADDOPTS=-x` thoát 1 sau 39 ca đạt và lỗi nền `tests/integration/test_auto_extraction_710.py::test_docx_table_has_real_structure_and_original_is_unchanged`. Cơ sở dữ liệu thử nghiệm đã được dọn.
- `git diff --check` thoát 0. Kiểm tra UI trực tiếp, model thật và cập nhật dịch vụ đang chạy chưa thực hiện.
