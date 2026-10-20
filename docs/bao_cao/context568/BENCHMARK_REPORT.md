# Context568 — Benchmark Luna chính, Qwen dự phòng

**Luna đạt ngưỡng đã chốt: 51/60 (85,0%) câu tri thức; Qwen trước đó 51/60 (85,0%).** Câu có đáp án: Luna 43/50 (86,0%), Qwen 44/50 (88,0%). Đây là đúng bộ64 câu, gồm60 tri thức và4 xã giao chấm riêng.

Đã chuyển và giữ cấu hình dùng thường: **Luna `cx/gpt-6-luna` qua9router làm chính; Qwen `qwen3.5-9b` làm dự phòng**. Áp dụng system chat defaults/chain và model policy của trợ lý admissions. Temperature0,2/max tokens5000/thinking budget0 và mọi thiết lập khác giữ nguyên. Đọc lại DB session mới và API backend đang chạy xác nhận đúng.

**Không sửa mã ứng dụng, tests hoặc scripts của repository.** Chỉ thêm runner/bằng chứng ignored và báo cáo theo yêu cầu. Không đổi prompt/hợp đồng output, nguồn, index, embedding, reranker, K, Quality Gate hoặc cache policy. Không reindex, xuất bản lại, restart, deploy, commit/push.

**Lượt này chưa chứng minh Luna tốt hơn tổng thể:** tổng điểm bằng Qwen; nhóm có đáp án giảm1ca, nhóm từ chối tăng1ca. Đây là kết quả một lượt trên từng model, không suy khác biệt có ý nghĩa thống kê hoặc ưu thế trên tài liệu khác.

## So sánh kết quả

| Nhóm | Qwen Context567 | Luna Context568 |
|---|---:|---:|
| Ô số liệu/mã/tên | 16/16 (100,0%) | 16/16 (100,0%) |
| Bảng phụ | 4/4 (100,0%) | 3/4 (75,0%) |
| Nhiều chỉ số/năm/mã | 5/5 (100,0%) | 5/5 (100,0%) |
| Liệt kê đầy đủ | 1/1 (100,0%) | 0/1 (0,0%) |
| Nối tiếp | 8/8 (100,0%) | 8/8 (100,0%) |
| Văn bản/ngoại lệ/chú thích/hình | 10/16 (62,5%) | 11/16 (68,75%) |
| Từ chối/làm rõ/tiền đề sai | 7/10 (70,0%) | 8/10 (80,0%) |
| Xã giao, ngoài mẫu số | 4/4 (100,0%) | 4/4 (100,0%) |
| **Tri thức, cần>=51/60** | **51/60 (85,0%)** | **51/60 (85,0%)** |
| **Có đáp án, cần>=43/50** | **44/50 (88,0%)** | **43/50 (86,0%)** |

4 ca Qwen FAIL→Luna PASS: P03, P11, P15, X09. 4 ca Qwen PASS→Luna FAIL: N19, M05, P10, P16. Không chỉ thử lại9ca lỗi, không loại ca mới thất bại hoặc ghép đáp án tốt từ nhiều lượt. [Đối chiếu đủ64 IDs](CASE_COMPARISON.md).

HTTP status: {"200": 64}; runtime errors: Không có. Đủ64 records, không thiếu/trùng; mọi timeout/schema/provider error vẫn FAIL. Citation khớp canonical source/hash/span/quote **79/79**. Trích dẫn hợp lệ không tự thành correctness PASS.

Qwen có93/93trích dẫn khớp, Luna79/79; số trích dẫn ít hơn không được coi là chất lượng tốt hơn, vì số câu trả lời/phạm vi câu cũng khác.

## Chỉ Luna cho lượt kiểm tra

Lượt này diễn ra 20/10/2026 16:20:38–20/10/2026 16:30:20 giờ Việt Nam. Dùng handler FastAPI thật, database/retrieval/reranker/provider thật; không dependency override hoặc fake model response. Không chạy lifespan nên không auto-seed/migration/Storage initialization.

Runner trong tiến trình riêng sử dụng cơ chế server-owned inference policy có sẵn, giao với tập provider được cấu hình rồi hạn chế còn đúng9router/Luna. Qwen chat fallback bị loại trước gọi upstream trong scope của benchmark; cấu hình Luna→Qwen dùng thường không bị tắt hoặc sửa trong lúc chạy. Embedding/reranker vẫn dùng model hiện có, không thuộc phép so chat model.

Usage audit xác minh 111 records, 0 lần gọi Qwen chat, 0 fallback; không có model khác. Các câu có đáp án quyết định bằng tọa độ và xã giao có thể không gọi LLM;64câu không đồng nghĩa64lần inference.

| Model quan sát | Status | Fallback | Calls |
|---|---|---|---:|
| gpt-6-luna | success | Không | 111 |

Prompt/completion tokens quan sát: 467903/20519; prompt lớn nhất10612. Chi phí tiền: NOT MEASURED, không suy đơn giá giả định từ tên model hoặc quy đổi token local thành phí.

## Nguồn và tính công bằng

- Application/code hash so với lượt Qwen cuối giữ nguyên; thêm kiểm trước/sau 1275 file app/tests/scripts/frontend source, không file mã thay đổi.
- Query/gold/rubric SHA256 `44f56799e5a07ccba7e8711c1a1cd66e99beec18a60458e1ee509cde2167d235`, không sửa câu hỏi/đáp án/tiêu chí. Giữ cả hai ngưỡng85%.
- Collection `col_admissions` epoch65; binding `bnd_fa71a57c9cf1`; source `ks_rev_ca1e7f16d9e0`; index `idx_rev_967891af9d5d`; generation `vg_a6e3190d11af`.
- Canonical `d466b624e1f873d0aae89ef319dc3d745088dfd9e9aeaa87fd09b61e799a604b`;262chunks/368facts và262vector points/payload seals giữ. Ngoài đúng2config records được người dùng cho phép, source/index/assistant/provider config seals giữ trong lượt.
- Quyền actor development hiện hành, collection/publication/snapshot checks vẫn chạy trong handler.
- Qwen baseline dùng TCP backend; Luna dùng ASGI handler để khóa provider riêng cho lượt. Cùng logic app, không phải một thí nghiệm giữ cố định network/worker/process/cache. Không quy mọi thay đổi độ trễ cho model.
- Độ trễ tri thức quan sát: Qwen P50/P95 676.83/21464.47ms; Luna 532.04/33349.57ms. Không suy SLA hoặc khẳng định hiệu năng chung từ một lượt.
- Chấm ô bằng exactsource coordinate/value/tuple/citation; chấm diễn giải và refusal theo rubric nguồn offline bởi Codex, không gọi judgeLLM. Đây là cùng bộ đã dùng để sửa mã, chưa có human gold signoff độc lập và chưa phải holdout. Khác biệt một lượt còn có dao động model.

## Giới hạn, kiểm tra và cleanup

Không fix bất kỳ ca FAIL nào trong nhiệm vụ này. Điểm số phản ánh Luna trên nguyên mã Context567, không phải kết quả sau tuning riêng Luna. Mọi failure được giữ nguyên.

Đã dọn 58 threads và14 gap records của lượt thử;0test threads/messages/gaps còn lại. Hội thoại/gap trước đó giữ, usage audit và private evidence giữ để đối soát. Không tạo DB test hoặc runtime Storage mới, không đụng thư mục runtime567 cũ đã bị policy chặn.

Tiến trình ASGI có14warning ghi log gap tiếng Việt do stdout mặc định Windows `charmap`; việc tạo14gap đã commit trước lệnh log theo mã hiện tại, và cả14record đều đã được dọn/kiểm.64HTTPresponses vẫn hoàn thành. Ghi nhận warning này là giới hạn harness/observability; không sửa mã, đổi encoding rồi chạy lại để che bằng chứng.

API update/readback, source/config/code/vector seals,64records, single-model route/usage và cleanup đã kiểm thực. Full Pytest/Ruff/FE build: NOT RUN vì không sửa mã; kết quả full Context5672785PASS/18FAIL/17SKIP là lịch sử, không phải fullPASS hiện tại. Retrieval ablation, holdout, concurrency/SLA và production NOT RUN.

Private receipts dưới `backend/storage/context568/`: `configuration-change-audit.json`, `run-complete.json`, `single-model-verified.json`, `handoff-verification.json`, `labels-final.json`, `summary.json`; không đưa corpus/prompt/credential vào báo cáo Git.
