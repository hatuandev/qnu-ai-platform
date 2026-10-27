# Context634 — Sửa và kiểm thử đúng luồng OCR Nemotron

Người dùng làm rõ yêu cầu là OCR. Kết quả native của Context633 không được dùng thay cho bằng chứng Nemotron. Đã sửa các ranh giới truyền engine và biểu diễn bảng, rồi chạy cả DOCX, PDF có chữ và PDF scan qua worker với `ocr_engine=nemotron-parse`.

## Kết quả OCR thật sau bản sửa cuối

| File tổng hợp | Engine quan sát | OCR bảng | Trạng thái nguồn |
|---|---|---|---|
| DOCX | docling+nemotron_parse; raw OCR nemotron_parse | 16/16 ô khớp | ready / READY_WITH_LIMITATIONS |
| PDF có chữ | nemotron_parse; raw OCR nemotron_parse | 16/16 ô khớp | ready / READY_WITH_LIMITATIONS |
| PDF scan chỉ có ảnh | nemotron_parse; raw OCR nemotron_parse | 16/16 ô khớp | review_required / NEEDS_ATTENTION |

Cả ba job thật completed, payload giữ engine Nemotron; không tái dùng artifact native để tính đạt. Tải lại ba file gốc HTTP200 và SHA256 khớp. Hash canonical/MD/structured/raw evidence, tọa độ raw bbox, source span và mapping trang đạt. Raw response dịch vụ được lưu, không có credential hay ảnh Base64 trong báo cáo. Model alias không xác minh độc lập phiên bản trọng số upstream.

Scan còn hai blocker: `visual_content_untranscribed` cho ảnh toàn trang và `heading_level_unresolved` cho Title chưa có cấp heading chắc chắn. OCR đã đọc đủ bảng; các blocker cấu trúc vẫn chặn source activation/publication. Không xóa cảnh báo, không tự duyệt. Dấu — vẫn ambiguous, không chuyển thành số 0; PDF native còn 16 literal chưa xác định vai trò cột, DOCX/scan có một limitation về ô dấu —.

## Bản sửa

1. `KnowledgeImportBatchCreateRequest` nhận `ocr_engine` tùy chọn. Service ghi lựa chọn vào metadata item và payload job, giữ khi retry và khi gọi processor trực tiếp. Payload cũ không có override vẫn giữ dạng cũ; request hash loại trường mới khi null để tương thích idempotency đã có.
2. Tách raw OCR và bản dẫn xuất: chuyển bảng HTML có ô rõ ràng sang GFM trước ghép nội dung native và Quality Gate. Phản hồi raw vẫn nguyên; không thêm từ điển dữ liệu hoặc thay giá trị ô.
3. Đối chiếu DOCX chỉ token hóa nội dung bảng đã đọc HTML, không tính tên thẻ/entity thành từ. Ngưỡng 0,9 và chặn nội dung không liên quan giữ nguyên. DOCX vẫn dùng cấu trúc nguồn để đối soát, đồng thời thực sự OCR ảnh PDF preview bằng Nemotron.
4. Lưu raw OCR của DOCX tại `ocr/preview.json` trong archive tài nguyên Office có checksum, cùng ảnh gốc nếu có. Giữ source hash DOCX, preview hash PDF và map trang; không đổi đường ảnh gốc hoặc fetch URI ngoài.
5. Extraction fingerprint lên `layout-v24-ocr-table-evidence` cho lần parse mới; không backfill, không sửa các revision đã lưu. Bump này đổi cache key qua helper hiện có, không tự chạy lại nguồn đang phục vụ.

File app sửa: schemas.py, services/import_batch_service.py, source_ingestion_service.py, source_extraction.py, qnu_docx_artifacts.py trong module knowledge. Thêm `backend/tests/test_ocr_ingestion_634.py`; cập nhật catalog test_ocr để kiểm cả Nemotron và không tự active khi thiếu cấu hình. Ca catalog riêng PASS/3,39s/exit0. Bản sửa ứng dụng khoảng vài chục dòng, giữ diff của các phiên khác.

## Kiểm chứng

- Tái hiện trước sửa: 4 FAIL/3 PASS cho bản test đầu, thêm ca entity FAIL và raw archive FAIL. Sáu ca lỗi riêng được xác nhận trước khi sửa tương ứng; không sửa assertion để làm xanh.
- Focused cuối: **134 PASS, 23 subtest PASS**, 49,81 giây, exit0. Chạy test_ocr_ingestion_634, test_source_layout_extraction, test_ingestion_mixed_regressions, test_qnu_docx_markdown, test_knowledge_candidate_and_import_batch, test_knowledge_v3_schema, test_nemotron_ocr_631. Chín ca regression mới đều nằm trong bộ này.
- Ruff đúng 5 file app và 2 file test: PASS, exit0. `git diff --check` đúng phạm vi PASS.
- Full Pytest cô lập: **3.835 PASS / 14 FAIL / 57 SKIP**, 439,24 giây, exit1; tổng suite vẫn FAIL. Lượt full đầu dừng ở giữa khi phát hiện cần lưu raw OCR DOCX; log partial được giữ, không tính nghiệm thu. Full cuối dùng database riêng, Redis DB14, temp workspace và storage local.
- Live API/S3/worker: `live_ocr.py --final`, `verify_live.py`, cwd backend, exit0. Lặp cùng Idempotency-Key HTTP201 trả cùng batch; đổi riêng engine với cùng key HTTP409/IDEMPOTENCY_CONFLICT, không chạy Paddle.
- API tự reload; worker được nạp lại sau khi kiểm tra không có job chờ/chạy để dùng bản sửa. Worker cuối PID wrapper2388 theo thời điểm khởi động. Giữ hạ tầng, defaults và provider/key hiện có. Không publish/vector/Compiler hay kiểm thử UI.

Collection CTX634: `col_508128d4b99b`; batch cuối `imp_batch_0cb3350c8684`. Hai nguồn DOCX/PDF đã được luồng import đặt active, scan pending; active_index=null cho cả ba, 0 index revision. Các fixture Context633 và collection Context634 được giữ để xem lại, có nhãn thử nghiệm và không dùng nghiệp vụ.

Bằng chứng gọn: [result.json](result.json). Runtime/log/XML và fixture tại `backend/storage/context634` và `context633` được Git ignore; không commit dữ liệu nhị phân, key hoặc corpus nghiệp vụ.

Lượt full ban đầu hoàn tất với 3.613 PASS/16 FAIL/60 SKIP/217 ERROR do thư mục tạm mặc định bị từ chối quyền; hai integration guard từ chối database không có tiền tố test. Không dùng lượt này để kết luận hồi quy. Hai preflight cô lập tiếp theo đều dừng trước pytest (guard env cũ; metadata khai báo index trùng), database test đã xóa. Harness cuối tạo database mới từ schema-only, không sao chép row/credential, dùng tiến trình mới nhận env trước import, temp trong workspace và chặn egress ngoài loopback. Bộ test ứng dụng và guard không bị sửa để vượt các lỗi môi trường.

## Đối chiếu full gate cuối

So với Context630: 13 failure ID và nguyên nhân giữ nguyên; 5 lỗi cũ đạt trong môi trường hiện tại. Một ID lỗi mới là `tests.test_context548_patch::test_api_whole_actual_document_uses_same_deadline_and_preserves_pending_scope`, do database test trống chưa có system_model_defaults. Đã chạy riêng đúng ID trong database mới có defaults chuẩn, không key/provider, inference mock và egress guard: **1 PASS/15,76s/exit0**. Không sửa mã app, guard hoặc assertion cho ca này; tổng full run trước đó vẫn ghi14FAIL.

Có 40 test trước PASS nay SKIP vì fixture cũ chỉ nhận các namespace database600–616 và comment sở hữu tương ứng; database634 không nằm trong whitelist. Giữ guard, không gán nhãn database của phiên khác để ép chạy. Tổng57SKIP không phải PASS; độ phủ toàn suite không đồng nhất baseline. 29 test Nemotron631 và9 regression mới634 đều PASS trong full run. Không tuyên bố toàn bộ ứng dụng đã nghiệm thu.

Các database thử/preflight/recheck đã xóa đúng database riêng do harness tạo; giữ artifacts trên D. Kiểm tra ứng dụng chính: ready HTTP200,7 collection/3 repository document/5 binding đúng trạng thái mong đợi, binding634 và defaults không đổi. Bảy file source/test giữ hash trong lượt gate cuối. Chín lượt tải MD/JSON/reader HTTP200.

[Đối chiếu test IDs và nguyên nhân](gate-comparison.json). UTF-8/LF, liên kết local, mẫu credential/Base64 và diff được kiểm ở bước chốt. Không commit/push.
