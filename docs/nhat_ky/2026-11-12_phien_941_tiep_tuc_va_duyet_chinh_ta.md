# Phiên 941 — Tiếp tục và duyệt chính tả theo từng vị trí

Người dùng yêu cầu giữ tiến độ khi soát lại sau lỗi và kiểm tra từng gợi ý trước khi duyệt chính tả.

- `backendV1/qnu/domains/ocr/review/automatic.py` khôi phục kết quả của lượt trước khi cùng văn bản, SHA-256, model, cấu hình, prompt và phiên bản ngữ cảnh. Lượt mới chỉ lập nhóm cho những đoạn chưa có kết quả. Nhóm con đã lưu có thể được khôi phục ngay cả khi lượt cha chưa ghi tổng hợp.
- `backendV1/qnu/domains/ocr/review/schemas.py` và `service.py` tiếp nhận các vị trí sửa của lượt duyệt, đối chiếu từng vị trí với gợi ý và áp lại trên văn bản gốc để kiểm tra bản gửi. Gợi ý bỏ qua được đối chiếu qua bản ghi quyết định đã lưu. Client cũ vẫn lưu được khi văn bản khớp chính xác với kết quả áp dụng toàn bộ gợi ý còn lại.
- FE V2 gửi từng vị trí áp dụng hoặc sửa tay và giải thích điều kiện tiếp tục lượt lỗi. Cập nhật ca trình duyệt theo thao tác “Hoàn tất duyệt” của giao diện hiện tại, kiểm tra đúng payload và phiên bản được chuyển sang chuẩn bị nội dung.

## Kiểm chứng

- Trước sửa, kiểm thử cô lập tái hiện lượt thử lại gửi lại cả 14 nhóm và thao tác duyệt trả HTTP 200 dù còn một vị trí chưa xử lý trong cùng đoạn.
- Từ root, `backendV1/.venv/Scripts/python.exe backendV1/scripts/run_isolated_tests.py tests/integration/test_ocr_text_review_651.py tests/integration/test_ocr_context_review_801.py tests/unit/test_ocr_spelling_batches.py tests/unit/test_ocr_context_review_801.py tests/unit/test_ocr_spelling_anchors_797.py -q` đạt 82 ca. Sau khi bổ sung phục hồi nhóm con, `...run_isolated_tests.py tests/integration/test_ocr_text_review_651.py -q -k 'reuses_only_compatible_progress or requires_each_span'` đạt 4 ca trên mã cuối, gồm đổi model, thiếu tổng hợp lượt cha, duyệt thiếu vị trí và xác minh nội dung gửi. Cả hai DB kiểm thử đã được dọn.
- Từ `frontendV2`, `node --experimental-strip-types --test src/lib/spelling-replacement-helpers.test.ts` đạt 5 ca, `node --test --test-name-pattern 'spelling review keeps the PDF URL' tests/studio-browser.mjs` đạt 1 ca Chromium với API giả lập. `npm run build`, Biome trên 5 tệp, Ruff trên 4 tệp và `git diff --check` đạt.
- Chưa chạy toàn bộ Pytest hoặc model thật. Thay đổi dùng bảng hiện có và không cần migration mới.
