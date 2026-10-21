# Context585 — Đặt timeout Luna 30 giây và thử lại P16

**Đã lưu timeout provider Luna từ 15 lên 30 giây. P16 thử lại PASS**, không có timeout trong lượt này. Model vẫn `cx/gpt-6-luna`; nguồn/index PDF staging giữ nguyên.

Đã thống nhất phạm vi trong cập nhật đầu lượt: chạy lại **riêng P16** để kiểm tra timeout, không gọi lại 63 câu còn lại hoặc sửa 5 lỗi khác. Benchmark Context583 vẫn **54/60 = 90%**; không ghép một lượt thử riêng vào điểm của bộ 64 câu.

## Cấu hình đã thay đổi

- Gửi đúng một `PUT` đến ModelOps API local hiện có, body chỉ `{"timeout_seconds":30}`. Actor được xác thực theo cơ chế hiện tại và handler kiểm quyền `ai.models.manage`; HTTP200.
- Fresh DB readback trước: 15 giây; sau cập nhật và sau test: 30 giây. Thay đổi áp dụng ở cấp provider 9router đang phục vụ Luna.
- Model, endpoint, credential, model capabilities và các provider khác không đổi. Dòng key thật trong DB không bị sửa bởi thao tác cấu hình. Service hiện có tự đồng bộ JSON key-pool mirror từ các dòng key làm nguồn chuẩn; đã đối chiếu đúng normalization này và `updated_at`, không coi đó là thay API key hoặc reset quota.
- Không đổi fallback cấu hình Qwen. Riêng phạm vi test tiếp tục giới hạn chat Luna như Context583 để tránh nhầm thành công do đổi model.

## Kết quả thực tế

| Kiểm tra | Kết quả |
| --- | --- |
| P16 — thiếu biến A/B/C | **PASS** theo rubric cũ |
| Trạng thái | `answered`, `VERIFIED_PROSE_FALLBACK` |
| Nội dung | “Chưa đủ điều kiện tính”; không gán biến thiếu bằng 0; không kết luận Đạt/Cần khắc phục |
| Citation | **6/6** đúng nguồn, revision, canonical hash, offsets và quote |
| Thời gian toàn luồng | **36.700,84 ms**, khoảng 36,7 giây |
| Usage quan sát | **5 Luna success**, 0 fallback, 0 model ngoài Luna |
| Runner | exit0, đủ đúng một ID P16 |
| Kiểm sau | PASS: timeout vẫn30, source/index/model/code/vector không đổi trong lượt thử, không có hội thoại test tồn lại |

30 giây là timeout cho **mỗi lần gọi provider**, không phải tổng thời gian trả lời RAG. Một câu hỏi có nhiều bước lựa chọn/kiểm chứng, nên tổng 36,7 giây với 5 lượt gọi là phù hợp. Một lần chạy thành công chưa chứng minh provider sẽ không bao giờ timeout; chỉ ghi nhận kết quả thực của lần thử này.

## Nguồn, cách chạy và giới hạn

- Cùng câu P16/rubric/source mapping của Context583, không đổi expected answer. Binding `bnd_12190866d5ec`, source `ks_rev_fef00606f91f`, index `idx_rev_bba8c17700d0`, generation `vg_a6e3190d11af`.
- Authenticated candidate snapshot do server xác minh; chạy `rag_service.ask` thật với persisted assistant profile, input preparation và provider thực. Không mock, không dependency override, không bật lifespan app hoặc restart.
- DB/MinIO/Qdrant được xác minh local development. Chỉ thao tác cấu hình timeout đã được người dùng giao; không migration/ghi nguồn/reparse/reindex/publish. Các lease/usage của inference ghi theo ModelOps bình thường.
- Seals app/tests/source/index/assistant, count/payload Qdrant khớp trước/sau lượt test. 327 điểm staging, 0 retrievable; nguồn chưa xuất bản. Không tạo thread/gap test persisted; giữ usage và evidence để audit.
- Lệnh thật, cwd repository, Python `backend/.venv/Scripts/python.exe`: `.antigravity-bridge/validation/context585_timeout.py` exit0; `context585_prepare_p16.py` exit0; `context585_p16.py` exit0; postcheck/adjudication offline exit0.
- Full64, full Pytest, frontend/build: **NOT RUN** trong Context585. Full Context582 lịch sử vẫn FAIL18. Không sửa mã ứng dụng, commit/push/deploy hoặc hạ Quality Gate.

Bằng chứng riêng, ignored: `backend/storage/context585/timeout-confirmed.json`, `update-intent.json`, `update-http.json`; thư mục `p16/` chứa manifest, responses, adjudication, single-model verification, run-complete và postcheck. Không lưu credential/private prompt vào báo cáo Git.

[Phân tích nguyên nhân cả 6 câu trước đó](../context584/SIX_FAILURE_ROOT_CAUSE.md). [Benchmark64 gốc](../context583/PDF_BENCHMARK64_REPORT.md).
