# Phiên #339 — Review kết quả E2E và tích hợp ModelOps sau #338

## Phạm vi

Review theo yêu cầu người dùng, không sửa runtime, không reset/migrate DB, không sửa qnu-sso. Đọc báo cáo #338, thay đổi adapter PaddleOCR/ModelOps/ingestion, kiểm tra DB read-only và chạy tests có phạm vi. Không chạy lại browser E2E hoặc gọi inference server bằng tài liệu thật.

## Bằng chứng đã đối chiếu

- Alembic DB: `20261011_independent_index`.
- `prov_rtx5090_vllm`: active, base URL `http://100.105.13.53:8000/v1`, timeout 60, có khóa cấu hình (không đọc/hiển thị giá trị), models `bge-m3`, `bge-reranker-v2-m3`.
- `prov_paddleocr_vl`: active, base URL `http://100.105.13.53:8080`, timeout 90, model `PaddleOCR-VL`.
- Kho `col_ae730507f5de`: epoch 2; 5 bindings active, 1 pending; 1 generation active; 1 batch partial_failed. Phù hợp một phần với báo cáo có một tệp lỗi, không tự chứng minh toàn bộ browser/inference E2E.
- Pytest có phạm vi (`test_paddleocr_adapter`, `test_vllm_reranker`, `test_knowledge_source_ingestion`, `test_adr012_runtime_contracts`): **20 passed**.
- Ruff phạm vi adapter/OCR/ModelOps/source ingestion/tests: đạt.
- Diagnostic dùng HTTP response giả lập, không phải E2E: PaddleOCR nhận HTTP 200 `{}` trả pages=0/text rỗng và không ném lỗi; adapter không truyền base_url vẫn trỏ server cụ thể và báo available.
- Quét tên tệp chứa mẫu khóa `sk_live_...` trong app/scripts/tests/docs/frontend/src/browser_tester: không thấy kết quả. Không phải audit secrets toàn hệ thống hoặc Git history.
- Docker CLI trong sandbox bị permission denied; không suy ra Docker người dùng chưa chạy.

## Findings

1. **P1 — OCR bỏ qua cấu hình/disable ModelOps**: adapter có địa chỉ gắn cứng khi không truyền base_url; `_extract_with_step` gọi adapter mặc định khi provider không tìm thấy/inactive. Vô hiệu hóa provider vẫn có thể gửi tệp đến server cũ. Không truyền timeout DB vào adapter. Cần fail-fast cho provider không hợp lệ, lấy endpoint/model/timeout từ DB và chỉ fallback theo chain cấu hình.
2. **P1 — Ranh giới trang/citations chưa đúng tài liệu nhiều trang**: PaddleOCR ghép text trang không có marker; source ingestion chỉ dùng raw_text và tạo manifest bằng chia đều số ký tự; fact extraction đưa toàn bộ Markdown vào page_number=1. Chunk thiếu page_number cũng rơi về 1. Cần giữ mapping trang từ OCR tới canonical/chunks/facts, test nội dung chỉ nằm trang 2/3. Tài liệu scan một trang không phủ lỗi này.
3. **P1 — Reseed overwrite có thể mất khóa/cấu hình**: `seed_default_providers(overwrite=True)` thay `api_key_encrypted`/extra_config bằng seed vLLM khóa trống/key pool rỗng, thay endpoint/timeout và còn xóa provider Ollama cũ. Đây là nhánh tồn tại chưa đáp ứng yêu cầu seed bảo toàn cấu hình; không gọi nhánh này trong review. Cần seed idempotent bảo toàn secrets và cấu hình người dùng, test hai lần với khóa đã lưu.
4. **P2 — Response OCR rỗng/malformed không báo lỗi chuẩn và confidence giả định**: HTTP 200 body rỗng được nhận là không lỗi; OCR service xây response success=True. JSON không hợp lệ/khác kiểu có thể phát sinh exception không chuẩn. Adapter còn gán confidence 0.98 mà không đọc điểm server. Cần validate response, phân biệt không có nội dung/lỗi protocol và ghi rõ confidence đo được hay không có.
5. **P2 — Báo cáo chưa đủ cho kết luận toàn diện**: #338 mô tả bộ nhỏ, không có bảng PASS/FAIL/BLOCKED/NOT RUN và không chỉ ra artifact browser/request traces có thể đối chiếu. Chưa có bằng chứng lưu trong báo cáo cho batch 100 tài liệu khác hash; model embedding thứ hai; reranker failure; cancel/retry/idempotency; activation giữa chừng/CAS; xóa nguồn gốc; migration trên dữ liệu cũ; full suite. Cần bổ sung bằng chứng hoặc đánh dấu chưa chạy, không suy từ 28 unit/regression tests thành E2E toàn diện.

## Kết luận

Tích hợp happy path có tiến triển và dữ liệu E2E tồn tại, nhưng chưa nghiệm thu toàn bộ quy trình. Đề nghị sửa findings và kiểm thử các ca còn thiếu, không chạy lại mọi thứ sau từng sửa nhỏ. Nhắc người dùng đổi khóa vLLM tạm sau kiểm thử. Tuân thủ skill clean-code: review có phạm vi và chỉ báo cáo căn cứ đã quan sát.
