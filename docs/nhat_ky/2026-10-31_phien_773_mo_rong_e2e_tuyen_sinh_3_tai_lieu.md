# Phiên 773 — Mở rộng bộ E2E Tuyển sinh Đa tài liệu (3 PDF, 53 Cases)

Ngày 2026-10-31. Triển khai và chuẩn bị toàn diện bộ kiểm thử E2E tuyển sinh QNU với 3 tài liệu thực tế (Multi-document Admissions RAG), mở rộng từ 1 tài liệu (19 câu) lên 3 tài liệu (53 câu hỏi), hỗ trợ kiểm tra ranh giới phạm vi tài liệu (scope boundary) và đối chiếu đa tài liệu/năm.

## 1. Dữ liệu và Bằng chứng Nguồn

Ba tài liệu PDF gốc đã được xác minh SHA256 và số trang (tổng 28 trang):
1. **Doc A (floor2026)**: `docs/tai_lieu/tuyen_sinh/TB điểm sàn 26.pdf`
   - 8 trang, SHA256: `236ab3573d6d683a760ed227512022d6c21a03ba5c147c32d4ed7b042f7c6d45`
2. **Doc B (info2025)**: `docs/tai_lieu/tuyen_sinh/Thong tin Tuyen_sinh_2025_QNU_V6_signed_signed_signed.pdf`
   - 13 trang, SHA256: `f427bb580ad0b2bea89b847a8ce31ffeb8611ea67fd1ba069fd7521ab7327b6b`
3. **Doc C (report2024)**: `docs/tai_lieu/tuyen_sinh/Báo cáo công tác Tư vấn tuyển sinh năm 2024_FINAL (1)_signed_signed-signed.pdf`
   - 7 trang, SHA256: `92353949628629e6dc63c5eed9aad587fd8e9a9db7c6d9814e2718a39ad6d96f`

## 2. Các Thay đổi Đã Triển khai

1. **Bộ Benchmark 53 Cases (`frontendV1/e2e/data/admissions-multi-docs.json`)**:
   - `F01`–`F19` (19 cases): Điểm sàn 2026 (scope riêng Doc A, gồm 3 unanswerable F17-F19).
   - `I25-01`–`I25-12` (12 cases): Thông tin tuyển sinh 2025 (scope riêng Doc B, chỉ tiêu, điểm đổi IELTS, điều kiện GDTC, học phí kỹ sư 102M, 6 phương thức, 2 unanswerable I25-11..12).
   - `BC24-01`–`BC24-12` (12 cases): Báo cáo tuyển sinh 2024 (scope riêng Doc C, số liệu nhập học 4.681/4.826, Bình Định 2.974, Gia Lai 609, THPT Trần Cao Vân & Nguyễn Thái Học 195, nữ 62.7%, fanpage 14.438, 29 trường THPT Bình Định, tham quan 2.152, khảo sát K47 Facebook 69.6%, học phí 66.7%, 2 unanswerable BC24-11..12).
   - `MX-01`–`MX-10` (10 cases): Đa tài liệu & kiểm tra ranh giới (7 cross-document answerable so sánh chỉ tiêu 2025 vs điểm sàn 2026, số nhập học 2024 vs học phí 2025; 3 scope boundary unanswerable MX-06..08 đòi hỏi model abstain khi hỏi dữ kiện ngoài tài liệu chỉ định).

2. **Cấu trúc Checkpoint & Trạng thái (`frontendV1/e2e/stages/session.ts`)**:
   - Bổ sung `AdmissionsDocEntry` và `state.admissions.documents[key]` lưu trữ độc lập theo `document_key` (`floor2026`, `info2025`, `report2024`).
   - Bổ sung `combinedIndex` lưu ID indexing-run chung chứa toàn bộ chunk của cả 3 tài liệu.
   - Giữ tương thích ngược hoàn toàn với `state.admissions.source` và `state.admissions.publication` (trỏ về Doc A).

3. **Stage Ingestion, Publication & Chat**:
   - `admissions-context.ts`: Nạp benchmark 3 tài liệu, hàm `checkAllSources()` xác thực hash cả 3 file.
   - `admissions-source.ts`: Upload tuần tự 3 tài liệu vào collection tuyển sinh chung, bóc tách OCR đủ 28 trang (8 + 13 + 7).
   - `admissions-publication.ts`: Biên soạn và review độc lập từng tài liệu qua ReviewGate; tạo 3 compiled documents; lập 1 indexing-run chung cho toàn bộ collection.
   - `admissions-chat.ts`: Hỗ trợ hỏi theo scope (`single` -> truyền `document_ids` riêng của tài liệu tương ứng; `all` -> truy vấn trên toàn collection); kiểm tra citation theo đúng SHA256 của từng nguồn; không retry câu lỗi; ghi nhận báo cáo chi tiết theo 4 nhóm.
   - `admissions.spec.ts`: Nâng timeout phù hợp 28 trang và 53 câu; kiểm tra hiển thị 3 file PDF trên giao diện.

4. **Regression Suite (`frontendV1/tests/admissions-multi-docs-773.test.ts`)**:
   - 6 test kiểm chứng toàn bộ phân vùng 53 cases, sha256 bytes PDF, 10 unanswerables, tính duy nhất của idempotency keys và không rò rỉ rubric vào question.

## 3. Kiểm chứng Cục bộ

- `npx vitest run tests/admissions-multi-docs-773.test.ts`: **6 PASS**, exit 0.
- `npx vitest run tests/admissions-replay-764.test.ts tests/e2e-capacity-735.test.ts tests/e2e-provider-selection.test.ts`: **22 PASS**, exit 0.
- `npm run test:e2e:typecheck`: **PASS**, exit 0.
- `npx biome check`: **PASS** trên cả 6 tệp E2E sửa đổi và tệp test mới.
- Scoped backend Pytest: **29 PASS**, exit 0.
- Scoped backend Ruff: **PASS**, exit 0.

## 4. Vận hành & Môi trường Live

- Đã cleanup phiên cũ `1da945adac7c` theo đúng quy định (`.\test-v1-e2e.ps1 cleanup`).
- Đã khởi tạo phiên E2E live mới `93faa11f0caf` (`.\test-v1-e2e.ps1 init --mode live`).
- Đã khởi động serve daemon (`.\test-v1-e2e.ps1 serve`), uvicorn API (cổng 64624) và frontend Vite (cổng 64625) đang lắng nghe ổn định.
- Chặn tại `provider-setup`: Database mới chưa có API keys của upstream server QNU / 9router. Theo quy chuẩn bảo mật tuyệt đối của QNU ModelOps, API keys không được truyền qua lệnh hay .env mà phải được nhập ẩn qua terminal tương tác một lần.

## 5. Lệnh Tiếp tục cho Người dùng

Mở PowerShell tại thư mục repo và chạy lệnh:
```powershell
.\test-v1-e2e.ps1 run provider-setup --headed
```
Nhập API key upstream (nhập ẩn) theo hướng dẫn trên màn hình. Sau đó các chặng live E2E tiếp theo sẽ tự động tiếp tục:
```powershell
.\test-v1-e2e.ps1 run model-discovery --headed
.\test-v1-e2e.ps1 run model-chat --headed
.\test-v1-e2e.ps1 run model-embedding --headed
.\test-v1-e2e.ps1 run model-rerank --headed
.\test-v1-e2e.ps1 run model-ocr --headed
.\test-v1-e2e.ps1 run navigation --headed
.\test-v1-e2e.ps1 run admissions-upload --headed
.\test-v1-e2e.ps1 run admissions-extraction --headed
.\test-v1-e2e.ps1 run admissions-compilation --headed
.\test-v1-e2e.ps1 run admissions-publication --headed
.\test-v1-e2e.ps1 run admissions-chat --headed
```
