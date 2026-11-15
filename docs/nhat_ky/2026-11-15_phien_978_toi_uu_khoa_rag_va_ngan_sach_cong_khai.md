# Phiên 978 — Tối ưu khóa RAG và ngân sách chatbot công khai

Người dùng yêu cầu xử lý hai điểm ưu tiên cao đã nêu trong review code.

- Qdrant và lần tải lại manifest chạy ngoài khóa PostgreSQL cấp đơn vị. Backend xác nhận lại quyền, generation, model embedding, phiên bản nguồn và tập chunk trước khi dùng kết quả. Đoạn xác minh cuối vẫn dùng khóa để bảo toàn trạng thái nguồn.
- Giữ cơ chế tính lượt nguyên tử đã có trong workspace. Thêm dự trữ ngân sách bằng Redis theo từng lần gọi ModelOps. Khi nhận số đo, giải phóng phần đã giữ và cộng token thực. Trường hợp usage chưa rõ giữ dự trữ đến hết ngày nghiệp vụ. Ngày được ghim theo thời điểm bắt đầu lượt. Tùy chọn không giới hạn vẫn ghi usage quan sát được.
- Bộ đếm theo ngày dùng cùng Redis key cho số đã quan sát. Báo cáo PostgreSQL cộng các bước trong lượt, gồm cả token của các bước đã chạy trước khi lượt gặp lỗi. Hủy hoặc lỗi trả lại lượt phiên theo cơ chế hiện có.
- Các tệp chính gồm `knowledge/index/search.py`, `modelops/usage/service.py`, `modelops/usage/scope.py`, `publications/limits.py` và `publications/public_service.py` trong `backendV1/qnu/domains/`. Hai tệp kiểm tra hồi quy ở `backendV1/tests/integration/`.

## Kiểm chứng

- Từ `backendV1`, harness `python scripts/run_isolated_tests.py` tái hiện hai ca lỗi trước sửa. Ca thu hồi nguồn trong Qdrant hết thời gian đợi khóa. Ca hai lượt cùng phiên trả cả hai thay vì chặn lượt thứ hai. **2 FAIL**, DB cô lập đã dọn.
- Sau sửa, cùng harness chạy bốn ca đích trong `test_index_api_647.py` và `test_publication_channel.py`. **4 PASS**, exit 0. Kiểm tra nguồn thu hồi, hạn mức phiên, tổng token 520 so với 400 ở lần sinh chính, và giữ ngân sách đồng thời. DB cô lập đã dọn.
- Ruff lint và format check trên tám tệp code/test **PASS**.
- Lượt unit đầu có 1.209 đạt và 4 lỗi. Cập nhật fixture `test_abbreviations_954.py` để mô phỏng truy vấn phiên bản và transaction mới. Chín ca trong file đó đạt sau chỉnh fixture, giữ nguyên điều kiện nghiệm thu.
- `python scripts/run_isolated_tests.py -q tests/unit` lần cuối có **1.211 PASS, 2 FAIL**, exit 1. Hai lỗi trùng [phiên 968](2026-11-14_phien_968_sua_dau_ra_rag_502.md): `test_legacy_source_deletion_718.py::test_deleted_source_can_request_new_permanent_preview_but_other_deletes_stay_blocked` và `test_migration_baseline_661.py::test_initial_schema_offline_sql_creates_v1_without_touching_legacy`.
- Harness trên `test_index_api_647.py`, `test_publication_channel.py`, `test_rag_verification_policy_672.py` và `test_answer_cache_956.py` có **56 PASS, 1 FAIL**, exit 1. Ca `test_rag_verification_policy_672.py::test_turn_scope_is_pinned_and_inherited_without_promoting_history_answers_to_evidence` nhận 504 sau khi mock provider ném `KeyError: evidence`. Cơ sở dữ liệu thử đã dọn.
- Chạy riêng ca 504 trong harness với `search.py` và `usage/service.py` từ HEAD nạp vào tiến trình pytest. **1 FAIL** với cùng 504 và `KeyError: evidence`. Đây là lỗi nền của workspace. Đã gỡ plugin thử tạm và dọn DB.
- Lượt toàn bộ qua `python scripts/run_sharded_tests.py --shards 8 --jobs 6 --label qnu-risk-review-optimizations tests -q` dừng sau khoảng 345 giây ở đợt đầu do nhiều ca tích hợp chậm. **INCOMPLETE**, không có kết luận tổng. Sáu harness xác nhận đã dọn sáu DB thử.
- Đo độ trễ tải thật, benchmark G3 100 câu, restart và triển khai **NOT RUN**.

Token dự trữ là ước tính từ ModelOps. Nếu provider báo số thực vượt dự trữ, backend ghi đúng số thực và xét hạn mức các yêu cầu tiếp theo bằng số đã ghi. Kết quả đo độ trễ dưới tải thật còn mở.
