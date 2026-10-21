# Phiên582 — Gỡ chặn PDF và mở rộng kiểm chứng

## Yêu cầu và phạm vi

Người dùng yêu cầu xử lý toàn diện các mục chặn PDF còn lại và mở rộng regression. Giữ thay đổi chưa commit, DOCX ổn định, nguồn thô, QNU RAG Markdown v1.0, Quality Gate và cấu hình model. Không commit/push/deploy hoặc tự duyệt proposal ngữ nghĩa.

## Thực hiện

- Đọc mã, diff, 70 blocker của revision 2 và raw evidence đúng hash; kiểm tra trực quan trang PDF có hình, ghi chú và khối mã.
- Tái hiện lỗi bằng canary; sửa header/dòng gộp, native/OCR, nền mã, footnote/footer, continuation/fragment, lưới literal và bảo vệ nguồn trước indexing.
- Mở rộng đối soát phát hiện thêm 7 tên trường bị tách `_`; dựng lại theo glyph baseline, giữ ma trận gốc và audit, không thay ký tự hoặc đoán nội dung. Thêm blocker khi glyph và ô khác chữ/số.
- Ghi receipt ảnh PDF riêng dựa trên bản chép Hình 1 người dùng đã xác nhận và kiểm tra trực quan bản export. Ảnh PDF đã lấy mẫu lại, không giả định bằng hash PNG DOCX; không duyệt proposal khác.
- Hai lượt official inline reparse tạo revision 3 và revision 4; không sửa các revision cũ. Revision cuối `ks_rev_fef00606f91f`, builder v5: READY_WITH_LIMITATIONS, 0 blocker.
- Đối soát 10 bảng / 695 ô khớp, 3 footnote, 1 code block, 7 glyph reconstruction. Có dependency cho dòng NV-30 bị cắt, giữ hai ô nguồn riêng.
- Service build vector hiện có chạy embedding/Qdrant thật: `idx_rev_bba8c17700d0`, 327 chunks/415 facts staging, parity327/327. Không publish; cổng trước xuất bản PASS với transaction giữ khóa rồi rollback.
- Không restart worker/BE/FE hoặc đổi model; inline dùng mã hiện tại. BE đang có reload sẵn. Cấu hình, Repository và dữ liệu ngoài phạm vi được kiểm seal từ cuối581 tới sau582.

## Kiểm chứng thật

Từ root repository, helper riêng gọi `backend/.venv/Scripts/python.exe -m pytest -q ... --basetemp=<owned-runtime> --junitxml=<report>` với cwd `backend`. PostgreSQL test có nonce, Storage local riêng; MinIO/Qdrant local được preflight, regression chặn egress bằng endpoint127.0.0.1:1; không dùng schema/Storage ứng dụng cho tests.

- Baseline focused102PASS/exit0.
- Canary10FAIL/1PASS/exit1: 4 failure hành vi, 6 verifier guards chưa có; exact IDs so với sau sửa.
- Focused cuối159PASS/exit0; 27 test mới PASS.
- Ruff11file PASS/exit0; diff check PASS.
- Full cuối **FAIL/exit1**, 2985PASS/18FAIL nền/17SKIP+23subtestsPASS, 473,27s. Đối chiếu580 theo ID/nguyên nhân:0newFAIL,0thay đổi trạng thái test cũ,18same causes.
- Một full sớm bị dừng sau khi phát hiện cần thêm guard glyph; không dùng làm kết quả cuối. Full cuối trên DB test mới, hash app giữ trong suốt lượt.
- Real source/hash/pair/projection/695cell/API200/vector/parity/prepublication PASS. Preview read-only đầu bị SQL từ chối khóa; lần cuối transaction giữ khóa và rollback đúng thiết kế, không ghi publication.
- Benchmark64, publication, FE build: NOT RUN trong lượt này.

## Dọn và bàn giao

Hai DB test đã được xóa sau kiểm nonce và kiểm tra không còn. Xóa Storage tạm bị kiểm duyệt tự động chặn (`blocked by policy`), giữ hai runtime, không tắt policy hoặc đổi công cụ để vượt chặn. Không xóa nguồn, index staging, usage/audit thật hoặc dữ liệu kiểm thử của phiên khác.

[Báo cáo chi tiết](../bao_cao/context582/PDF_BLOCKERS_AND_VALIDATION.md), [test IDs](../bao_cao/context582/VALIDATION_REPORT.md). Evidence riêng: `backend/storage/context582/`; không đưa corpus/raw OCR vào Git. Source/model/hash đã kiểm không đồng nghĩa benchmark RAG đạt hoặc nguồn đã xuất bản.
