# Phiên 879 — Metadata có dẫn chứng và biên soạn kết hợp

Triển khai bước 3–4. Nhận diện metadata từ văn bản đã bóc tách và ghim phiên bản khi biên soạn. Dùng JSON đã có để lưu trường chuẩn và thuộc tính linh hoạt có kiểu, dẫn chứng, phạm vi và nguồn tạo đề xuất. Phân biệt năm ban hành, năm dữ liệu và ngày hiệu lực. Giữ nguyên các trường chưa xác định khi trích đoạn không chứng minh được.

- Chế độ Biên soạn nhanh có lựa chọn AI bổ sung. Worker giữ văn bản, bảng và dẫn chứng như bản nhanh. Phần AI dùng các nhóm đã ghim qua ModelOps. Chia lại phần có phản hồi xác định bị cắt. Các đề xuất bổ sung nằm riêng trong JSON của Compiler.
- Giao diện đăng ký cho người dùng chọn từng đề xuất sau khi đọc trích đoạn và vị trí nguồn. API kiểm lại phạm vi, trích dẫn và xung đột rồi ghim metadata đã xác nhận vào phiên bản. Thuộc tính linh hoạt được lưu cùng metadata. Bộ lọc động thuộc bước 5.
- Giữ quy trình duyệt và phát hành. Sau phát hành, chỉ mục đi theo cơ chế nền của bước 1–2. Bước 3–4 dùng các cột JSON hiện có.

## Kiểm chứng

- PASS — backend tập trung 51 ca qua harness DB cô lập, gồm xác nhận metadata, biên soạn nhanh, chia phần, đọc tiến độ và chính sách metadata. Lượt có hồi quy tự lập chỉ mục đạt 61 ca.
- FAIL — bộ backend diện rộng chạy fail-fast dừng sau 659 ca đạt, tại test_rag_modelops_budgets_767.py::test_window_zero_records_bounded_bytes_and_keeps_whole_evidence. Fixture truyền actor=None vào đường kiểm tra quyền. Phần còn lại của bộ diện rộng chưa chạy.
- PASS — 41 ca Vitest tập trung, Biome trên 8 file và npm run build gồm TypeScript.
- FAIL — lượt FE mở rộng có 61 ca đạt và một lỗi ở v1-publication.test.ts. Assertion cũ yêu cầu URL kết thúc bằng /draft trong khi luồng đọc theo mục dùng /draft?group_by_source=true.
- PASS — Ruff có phạm vi và git diff --check. Backend chạy từ root với uv run --project backendV1 --frozen --extra dev python backendV1/scripts/run_isolated_tests.py. FE chạy từ frontendV1.

Kiểm thử mô hình bằng provider giả trên loopback và PostgreSQL cô lập. Chưa chạy luồng live trên tài liệu thật. Không đổi cơ sở dữ liệu ứng dụng, dịch vụ đang chạy hoặc chỉ mục hiện hành.
