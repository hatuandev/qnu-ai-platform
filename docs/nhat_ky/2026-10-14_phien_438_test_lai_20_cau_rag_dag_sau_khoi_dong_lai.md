# Phiên #438 — Test lại 20 câu RAG/DAG sau khi khởi động BE và worker

## Mục tiêu

Chạy lại cùng 20 câu đại diện sau khi người dùng đã khởi động lại backend và worker, để tách lỗi môi trường khỏi lỗi chất lượng RAG/DAG. Phiên này chỉ kiểm thử và ghi nhận, không sửa code.

## Thực hiện

- Lệnh: `.venv\\Scripts\\python.exe -X utf8 -u -m scripts.evaluate_evidence_417 --ids 1,3,5,6,9,11,13,16,19,22,25,38,48,51,62,66,75,80,81,82 --routes dag,rag --output storage/admissions_eval438_smoke20.json`
- 40 lượt: 20 DAG và 20 RAG.
- Artifact: [admissions_eval438_smoke20.json](../../backend/storage/admissions_eval438_smoke20.json).
- Không reset DB, không reindex, không publish, không đổi model/provider/config.

## Kết quả

- DAG: 20/20 HTTP 200; `supported=4`, `partial=11`, `missing=5`.
- RAG: 19/20 HTTP 200; `supported=3`, `partial=12`, `missing=3`, `conflict=1`; câu 38 HTTP 502 `EVIDENCE_TARGET_SCOPE_INVALID`.
- Độ trễ trung bình: DAG 33,37 giây (P95 43,22 giây), RAG 27,17 giây (P95 40,28 giây).
- ModelOps: 304 lượt `gpt-oss:120b` thành công, 3 lượt fallback `gemma4:31b` thành công; không có lỗi provider trong `served_models`.
- Fingerprint xác nhận `code_unchanged`, `configuration_unchanged`, `publication_unchanged` đều true.

## Vấn đề được ghi nhận, chưa sửa

- RAG câu 38 bị scope validation 502 khi câu hỏi không ghi rõ trường đích.
- Câu 19 và 80 không bind được số liệu/quote nên bị missing; câu 25 conflict/missing; câu 82 chỉ partial.
- Câu 5 có nguy cơ cộng nhầm chỉ tiêu bổ sung vào chỉ tiêu chính quy; câu 6 chưa phân biệt 53/56/28.
- Câu 9 thiếu danh sách PT1–PT5; câu 11/13/16/22/48/62/66/75 bị thiếu qualifier hoặc bị audit hạ partial.
- Tài liệu 2025 vẫn lọt candidate selection ở một số câu hỏi 2026, làm tăng nhiễu temporal; câu 66 là trường hợp lịch sử có chủ đích.
- Độ trễ P95 cao; cần quan sát planning/retrieval/verification trước khi chạy full82.

Chi tiết theo từng câu nằm trong [báo cáo kiểm thử](../kiem_thu/2026-10-14_20_cau_rag_dag_sau_khoi_dong_lai.md).

## Kiểm thử/lint

Không chạy lại lint hoặc test suite vì phiên này không thay đổi mã nguồn. Focus suite 95 và Ruff của phiên triển khai trước vẫn giữ nguyên kết quả trong nhật ký #437.

## Bài học và bước tiếp theo

Kết nối sau restart đã ổn định hơn (40/40 không lỗi vận chuyển ngoại trừ một lỗi scope 502 có cấu trúc), nhưng tỷ lệ `supported` còn thấp. Cần xử lý scope, số liệu và temporal/qualifier audit trước khi mở rộng sang toàn bộ 82 câu và Ragas.
