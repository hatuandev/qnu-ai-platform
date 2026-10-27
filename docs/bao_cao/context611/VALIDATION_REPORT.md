# Context611 — Kiểm chứng đóng gói và checkpoint compiler

Ngày23/10/2026. Yêu cầu sửa packing/checkpoint rồi chạy ba DOCX2024–2026 bằng GPT-OSS medium/output8192; giữ nguồn, Quality Gate, không reindex/publish/commit/push. Triển khai hoàn tất phần này; **nội dung compiler chưa nghiệm thu** vì vượt cardinality của hợp đồng tổng.

## Thay đổi

| File/hành vi | Thay đổi phục vụ yêu cầu |
|---|---|
| compilation_runtime_schemas.py |Policy output/context/effort, tổng calls; cặp job/version khi tiếp tục. Client vẫn không tự cấp budget hoặc chọn model. |
| compilation_modelops.py, wiki_build.py |Cùng policy cho planner/request/configuration hash; effort riêng truyền vào ModelOps; timeout lấy route provider. |
| modelops/schemas.py, providers/openai_adapter.py, services/inference_service.py |reasoning_effort low/medium/high cho request thực và streaming; adapter không hỗ trợ báo lỗi, không đoán từ thinking_budget. |
| compilation_engine.py |Request trích xuất/review tính riêng; tiền kiểm tối thiểu toàn plan sau selection; checkpoint ordinal/schema/instruction/payload/config; chặn trước calls/time limit, không reset tổng budget; feedback dài được thu gọn mà không cắt nguồn. |
| compilation_review.py |Chia review theo assertion khi cần, giữ toàn bộ raw packet/context; kiểm đầy đủ item IDs và missed/deferred ledger. Giữ sửa608 về temporal targets/empty draft. |
| compilation_coverage.py |Dùng chung trường lặp của existing assertions, mở rộng ngược phải khớp hoàn toàn; giữ hai coverage audits độc lập và tối đa một targeted repair. |
| compilation_checkpoint.py |Started intent trước network, completed candidate sau Storage roundtrip; source/config/actor/hash checks, uncertain không gửi lại; chuỗi audit riêng. |
| compilation_service.py |Authenticated/versioned/idempotent resume; một parent chỉ một child; ghim packet cache; giữ source hash, total counter và receipt; không approval/publication. |

Không migration DB hoặc frontend/parser changes. Giữ toàn bộ thay đổi Context608 đã có trước611; chỉ thêm11app files thay đổi trong phạm vi611 (10file sửa,1file checkpoint mới). 458Python appfiles ở cuối;457đầu611. Postcheck exacthash xác nhận mọi file khác giữ nguyên. [Thiết kế](DESIGN.md).

## Regression thực chạy

Cwd repo root D:\DuAnPhanMem\qnu-ai-platform. Helpers .antigravity-bridge/validation/context611_*.py dùng backend/.venv/Scripts/python.exe; child pytest cwd backend. OPENBLAS_NUM_THREADS=1 chỉ trong shell/process, không app config. Các DB test tách riêng, LocalStorage riêng, endpoints test127.0.0.1:1 và ownership guard. Không chạy inference thật trong unit/full regression.

| ID/lượt | Kết quả | Exit/giới hạn |
|---|---|---|
| Repro trước sửa |4FAIL,1SKIP |1; fixture handler chưa cho prefix611 nên SKIP, không coi đã tái hiện handler lúc này |
| Focused-new |5PASS |0; kiểm đầu về payload/resume/uncertain/version/handler |
| Focused-logic |53PASS/1FAIL |1; fixture sizing chọn input quá lớn; sửa fixture thêm cả fit/oversize controls, không nới gate |
| Focused-final trung gian |185PASS/4FAIL |1; tương thích mocked adapter, audit endpoint cũ và mục tiêu Storage failure injection được sửa đúng hành vi |
| Focused-release trung gian |126PASS/1FAIL |1; tổng-budget test cần kiểm điểm preflight sớm mới |
| Focused-final trên release DB |22PASS |0,71,94s |
| Concurrent-final |2PASS |0,14,80s; cùng-resume và cạnh tranh bằng fresh intent |
| Checkpoint-final |59PASS |0,60s; gồm source/config/hash/quyền/concurrency/compaction và safe known prefix |
| Ruff cuối14files |PASS |0; log/command receipt ruff-final-run.json |
| Full chốt final-checks |**3586PASS/18FAIL/17SKIP,+23subtestPASS** |**1**,769,57s; không coi fullPASS |
| Exact ID/cause compare với full608 |PASS |0;22test mớiPASS,0newfailure,0cause đổi,0ID mất,0lỗi nền được che |
| UTF8/noBOM/LF14source+tests, diff check |PASS |0; kiểm bytes và tiếng Việt |

Hai lượt bị dừng giữ **INCOMPLETE**: release-fixes chạy trùng DB với một focused khác được dừng để tránh nhiễu; full-final ở release-checks bị dừng khi live compiler phát hiện ranh giới coverage request cần sửa tiếp. Full chốt dùng DB mới final-checks sau khi sửa và kiểm trọng tâm, có JUnit/exit receipt riêng. Không ghép lượt dở với full chốt.

Baseline lịch sử608:3564PASS/18FAIL/17SKIP,+23subtestPASS. Nguồn app đầu611 khớp checkpoint608; không chạy lại full baseline thừa. Đối chiếu từng ID/cause: [TEST_ID_COMPARISON](TEST_ID_COMPARISON.md). Các test cũ về quyết định/audit giữ hợp đồng; test Storage failure nay nhắm theo nội dung final bundle thay cho “lần save thứ2” vì checkpoint thêm durable writes trước đó.

## Compiler ModelOps thật

96calls, đều gửi medium/output8192, cùng gpt-oss:120b/0fallback,96finishstop/0length exhaustion. Max5295output,6244input; usage482090input/151499output. Tất cả request gửi qua budget guard, maxreserve24000/24000. Không có upstream effort echo nên chỉ xác minh medium đã gửi, không khẳng định router thực thi mức này phía sau.

54calls đầu gặp coverage payload25459>24K, chặn trước call tiếp theo. Lossless compaction giảm còn23076, đọc lại52completed/2rejected và tiếp tục chỉ42calls mới. Cuối có91completed/5contractrejected,96ordinal duy nhất, parent refs54giữ nguyên, object/audit readbackPASS. Không có started/uncertain inference stage nào được resend.

Toàn compiler **FAIL** trước synthesis:92entities>64,145assertions>128. Không có exactduplicate để gộp; đây là các candidate, chưa là facts đã duyệt. Không tăng contract cap hoặc bỏ bớt để đạt PASS; không chạy lạiLLM tại lỗi ghép xác định. Job cuối kc_182025997c28481f83f32890cc2ce77f/uncertain/bundle null. [Báo cáo live và giới hạn](LIVE_COMPILER_REPORT.md) phân biệt các receipt gốc với đối soát job mới chính xác.

## Bất biến và dọn môi trường

DB/MinIO/Qdrant xác minh development/loopback trước chạy; migrations chỉ create_all ở DB sở hữu, không migration shared DB. Inference credentials giải quyết qua ModelOpsDB, không đưa vào .env hoặc DBthử. Typed defaults metadata inactive/no credential được copy vào DB regression để giữ fixture cũ, không kích hoạt inference tại đó.

Postcheck sau full: nguồn DOCX hashes, shared collection/binding/revision/index/provider/defaults/assistant rows giữ exacthash. Primary vẫn gh/gpt-6-luna; chỉ route experimental ở harness chọnGPT-OSS. Qdrant2943points/full payload khớp baseline602,0retrievable; không reindex/publication. App hash ngoài11file611 giữ nguyên; finaltestedcode14file hash giữ saufull.

Bốn DB sở hữu611 đã dọn sau exactname/nonce comment và xác nhận không còn:

- live-checks: qnu_test_context611_dda104231190.
- runtime-checks: qnu_test_context611_d27c688eeb4b.
- release-checks: qnu_test_context611_1263e5563629.
- final-checks: qnu_test_context611_394fea3af140.

Storage artifacts giữ lại theo chính sách bảo vệ và nhu cầu đối soát; không thử vượt chặn cleanup. Không xóa dữ liệu thật, restart/reparse/publish, stage/commit/push. FE/build, benchmark64 và browser/published E2E **NOT RUN** vì ngoài phạm vi.

## Bàn giao

Chức năng đóng gói/checkpoint được kiểm bằng unit/handler/DB và live resume thật. Chưa APPROVED toàn compiler hoặc nguồn. Điểm tiếp theo cần thiết kế là cách giới hạn/nhóm các candidate trong hợp đồng tổng có provenance và kiểm chứng đầy đủ, đồng thời review relevance/scope; không đơn thuần tăng số token hoặc cap danh sách.

Evidence local backend/storage/context611: final-checks/full-final.xml và full-final-run.json; test-id-comparison.json; ruff-final-run.json; code-final-verification.json; live-summary.json; checkpoint-durable-summary.json; shared-row-verification.json; postcheck-final.json; isolation receipts trong bốn thư mục checks. Nội dung private không đưa vào Git.
