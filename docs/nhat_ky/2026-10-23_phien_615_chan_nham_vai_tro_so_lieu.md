# Phiên615 — Chặn nhầm vai trò số liệu trong compiler

Người dùng yêu cầu sửa chỗ nhầm, chỉ test câu hỏi liên quan; giữ model/nguồn/Quality Gate, không reindex/publish/Git. Đã đọc AGENTS, memory, diff, code và các skill clean-code/backend/ingestion/ModelOps.

Nguyên nhân: giá trị có trong bảng được dùng để xác nhận nhãn chỉ số chưa có căn cứ; cả extractor và reviewer cùng nhầm kết quả đã nhập học thành chỉ tiêu. Thêm binding literal metric/cột, kiểm đúng ô, context và header; policy v4/config hash mới, giữ đọc bundle cũ.

Trước sửa 9 FAIL/3 PASS; cuối 19 PASS/0 FAIL, exact 9 lỗi được khép và 7 ID mới PASS. Ruff6 PASS. Chỉ chạy `python -m pytest -q backend/tests/test_compilation_metrics_615.py --junitxml=backend/storage/context615/focused.xml` từ root bằng Python3.12 venv; exit0/5,68 giây. Full/64/FE NOT RUN theo phạm vi người dùng.

Thử thật một câu hỏi 5.081, hai lượt/8 inference GPT-OSS medium8192, all stop/0fallback. Lượt sau dùng lại đúng 3 receipt hoàn tất khi harness dừng cục bộ, chỉ gọi thêm review còn thiếu. Không còn khẳng định tổng chỉ tiêu; binding/scope/header vẫn chưa đạt, server chặn dù review nói supported. **Chỉ nghiệm thu guard, chưa APPROVED khả năng trích xuất ngữ nghĩa của ca thật**.

Nguồn/config/shared metadata hashes trước/sau giữ; DB/MinIO/Qdrant loopback, DB nghiệp vụ chỉ đọc, ModelOps ghi usage theo luồng thật. Không tạo DB test, không nạp dữ liệu thử vào kho/vector; Storage receipt riêng giữ theo policy. Không reset/migration/reindex/publish/restart/stage/commit/push.

Chi tiết file, lệnh, test ID và giới hạn: [báo cáo615](../bao_cao/context615/REVIEW.md). Bước sau nếu được giao: cải thiện tạo binding từ context nguồn/header; không đánh đồng guard PASS với model đã hiểu đúng hoàn toàn.
