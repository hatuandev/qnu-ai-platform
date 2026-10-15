# Phiên 473 — Sửa metric header và bổ sung context cùng hàng nguồn

## Mục tiêu

Sửa lỗi từ chối câu “Điểm chuẩn ngành Sư phạm Toán học và Công nghệ thông tin các năm gần nhất là bao nhiêu?” dù kho đã có bảng. Dùng skills RAG, Backend và clean-code; không thêm từ điển ngành/đáp án hoặc thay cấu hình model.

## Thay đổi

- `backend/app/modules/rag/row_answer.py`: không loại scope unit là table header khỏi MetricScope. Header/năm/đường dẫn cột gốc là bằng chứng cấu trúc, không yêu cầu intro luôn phải nêu metric bằng văn xuôi. Bước này vẫn không nhận số liệu ô.
- Header/intro gốc được liên kết đến nhiều entity rows: mở rộng ID theo cùng binding/index/source/hash/start/end. Không ghép chỉ vì đoạn văn giống chữ; không chuyển header giữa nguồn.
- Chỉ dẫn SELECT/AUDIT phân biệt năm dữ liệu với ngày văn bản/đồng hồ, xử lý “gần nhất” không yêu cầu năm số trong câu; ưu tiên phạm vi năm chung gần nhất. Chưa phải bộ lập kế hoạch thời gian xác định hoàn toàn.
- `backend/app/modules/rag/row_answer_contract.py`: `complete_audit_context` giữ nguyên mọi ô đã chọn, chỉ bổ sung context auditor yêu cầu thuộc scope/notes của các hàng đang chọn. Vẫn cần hai lượt đồng ý chính xác tập ô, cờ compatible/scope/complete và không conflict. Context lạ/nguồn khác vẫn bị kiểm tra subset và validation chặn. Giữ toàn bộ điều kiện cũ; không chuyển sang free generation khi bị từ chối.
- Log mọi `_missing` kèm snapshot/reason/số điều kiện thiếu, không ghi câu hỏi hoặc nội dung bí mật vào log mới.
- `backend/tests/test_row_metric_headers.py`: tám ca generic về header định nghĩa metric/năm, đa ngành, header dùng chung, không mượn nguồn, thiếu metric/ID sai, thiếu entity, auditor bổ sung đúng/sai nguồn.

## Tái hiện và kiểm chứng

- Trước sửa: test mới 3 failed/2 passed; mất header, câu đa ngành bị từ chối và không đi tới missing-entity audit.
- Biên header dùng chung: 1 failed/5 passed trước sửa mở rộng theo tọa độ.
- Biên auditor bổ sung context cùng hàng: 1 failed/7 passed trước sửa closure.
- Sau sửa: 43 test trọng tâm đạt; Ruff các tệp sửa đạt.
- Full lần đầu (chưa chứa hai ca context mới nhất): 1462 passed/11 failed/16 skipped, 193.29s. Không dùng lượt này làm final gate của mã cuối.
- Final gate mã cuối: **1464 passed/11 failed/16 skipped/0 errors, 190.59s**; `backend/storage/pytest473_verified.xml` và `.log`. So sánh exact classname/name của11ca fail với `pytest470_final.xml`: không có chênh lệch. Ruff toàn Backend đạt, chỉ cảnh báo ACL ở artifact cũ; không chỉnh quyền/xóa artifact để giấu cảnh báo. Không sửa Frontend nên không chạy Vite build.

## Probe thật, giữ cả kết quả lỗi

Dùng lại script/hàm trace giai đoạn4, chỉ thay bộ câu hỏi của harness trong tiến trình chẩn đoán, không thay hàm runtime hoặc câu trả lời. Model nhận câu hỏi và nguồn thực, không nhận đáp án kỳ vọng. Không kiểm thử HTTP/UI; chưa chạy 20/82.

- `backend/storage/rag_metric_473/first_report.json`: câu gốc qua metric nhưng audit từ chối vì thiếu các context IDs, mặc dù tập ô đồng ý. Điểm sàn gặp JSON invalid (model lặp quá số missing_constraints), sau một lần repair vẫn lỗi; năm2037 từ chối đúng.
- `context_report.json`: sau context closure, câu gốc answered, primary Qwen; regression điểm sàn lỗi provider unavailable (fallback Cloudflare HTTP502), không coi là đạt; năm2037 tiếp tục từ chối.
- `coherent_report.json`: bản cuối thử câu gốc và điểm sàn đều answered, mỗi câu ba lượt generate primary `qwen3.5-9b`, không fallback. Thời gian service trace toàn lượt khoảng59.36s/6.80s; không suy p95 từ hai mẫu.
- Câu gốc giữ đúng bốn ô 2024/2025: Sư phạm Toán26.5/25.85, CNTT16.5/21.5. Còn kèm hai dòng tham khảo SP Toán2023/2024 từ nguồn cũ, một dòng2024 trùng ý; chưa coi việc chọn phạm vi gần nhất/rút gọn đã hoàn hảo, chỉ dẫn mới chưa loại hết dòng thừa.
- Điểm sàn giữ20/–/–/20 và chú giải, note2/a/b cùng scope; ghi chú vẫn dài, có điều kiện nhóm khác được trích nguyên văn với phạm vi rõ.
- Đối chiếu19citation raw spans/hash với canonical DB: không có lỗi. Các fingerprint config/pub/targetdata/collectionmetadata/inventory không đổi ở cả ba báo cáo và lần kiểm tra sau probe.
- Tám lượt chat được thử tổng cộng; có tạo hội thoại/usage/key health/gap bình thường, có lượt rollback do lỗi. Không xóa các vết này. Không phát sinh OCR, migration/reset, reparse/reindex/publish, đổi model/config, restart/deploy hoặc git stage/commit/push trong phiên.

## Giới hạn và bước tiếp

Đã xử lý lỗi mất cấu trúc header và từ chối chỉ vì hai reader khác context list, không gỡ kiểm tra groundedness. Vẫn còn nhiễu dòng lịch sử/notes dài và tính biến thiên JSON/upstream của model thật. Cần test đa dạng theo nguồn, không suy toàn bộ RAG ổn từ hai ca answered. Người vận hành cần nhận mã mới vào BE trước khi thử lại qua giao diện.
