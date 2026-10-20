# Context562 — Báo cáo kiểm chứng

Ngày: 2026-10-20. Trạng thái: **ROUTING_VERIFIED / LIVE_KNOWLEDGE_E2E_BLOCKED**. Không báo toàn hệ thống APPROVED.

## Môi trường an toàn

Đã xác minh ENVIRONMENT development, DB/MinIO/Qdrant ở loopback trước chạy. Pytest dùng DB riêng có nonce và ownership comment, Storage runtime riêng; MinIO/Qdrant/Redis của test trỏ loopback port không phục vụ. AUTO_MIGRATE/AUTO_SEED tắt. Chỉ `create_all` trong DB disposable; không migration hoặc đổi schema DB ứng dụng. Bản sao ModelOps phục vụ baseline nằm mã hóa trong DB test, không xuất key/log.

Kiểm API thật dùng development DB và published sources hiện có, chỉ ghi các hội thoại test do phiên này tạo và usage audit của các model call thật. Các conversation test đã xóa theo ID/first-message/actor ownership; usage audit được giữ. Sáu hội thoại test tổng cộng đã dọn trong DB. Không xóa hội thoại người dùng.

## Kết quả đã chạy

| Kiểm tra | Kết quả | Exit | Giới hạn |
|---|---|---|---|
| Red routing/SSE trước sửa | 7 FAIL | 1 | Chứng minh lỗi cần sửa |
| Red session ownership | 1 FAIL | 1 | Chứng minh ID đơn lẻ cho phép nối vào phiên |
| Focused routing/history/acts/safety/auth | 277 PASS | 0 | Trước ba test bổ sung cuối; tất cả được full run cuối bao phủ |
| Compatibility sau đối chiếu full đầu | 36 PASS | 0 | Workflow/history/permission/API tests |
| Full đầu | 2660 PASS / 24 FAIL / 17 SKIP + 23 subtests | 1 | 5 mock DB cũ và 1 permission-contract mới được sửa; giữ log |
| Full cuối | **2666 PASS / 18 FAIL / 17 SKIP + 23 subtests** | **1** | 18 lỗi nền vẫn FAIL |
| Scoped Ruff | PASS, 21 file Python | 0 | Không lint toàn repo |
| Corpus độc lập | 116/116 đúng expected behavior | 0 | Rule/contract corpus, không phải model accuracy ngoài mẫu |
| Multi-turn gold | 20/20 PASS | 0 | Structured model output stub; kiểm scope/rewrite/call count |
| Qwen thật, resolver qua ModelOps | 3/3 PASS | 0 | Ba mẫu, không phải benchmark accuracy tổng quát |
| ASGI app/services/infrastructure thật: greeting + thanks | 2/2 PASS | 0 cho từng HTTP 200 | Spy forward call thật, không thay model response; không phải TCP/browser E2E |
| ASGI Knowledge mixed | HTTP 409 EVIDENCE_CONTEXT_MISSING | 1 cho script live | Dừng chuỗi Knowledge→thanks→year-followup, không gán PASS các bước chưa chạy |
| Sandbox trình duyệt | Greeting/thanks, debug SOCIAL/0 calls PASS | N/A | Trình duyệt đang có dev actor; test anonymous quyền riêng ở handler |
| Chat public trình duyệt | Greeting/meta, A/B, đổi đoạn và tải lại PASS | N/A | DB kiểm A có 3 lượt, B có 1 lượt, hai server IDs riêng |
| Widget nhúng trình duyệt | Greeting→thanks PASS | N/A | DB xác nhận 2 lượt cùng server ID, harness local đã xóa |
| Frontend behavior tests | 6 PASS | 0 | 3 URL/session và 3 thực thi mã widget với DOM/stream giả |
| Biome / build + TypeScript | PASS (10 file / build + TypeScript) | 0 | Biome override LF theo AGENTS; không sửa config |

Tất cả số PASS ở các hàng focused có thể trùng nhau; không cộng chúng thành tổng test độc lập.

## Regression chính xác

Baseline Context561: 2494 PASS / 18 FAIL / 17 SKIP +23 subtests. Full cuối tăng 172 ID mới, tất cả PASS. **Không có ID chung đổi trạng thái, không có ID bị xóa, toàn bộ 18 ID lỗi và nguyên nhân đầu tiên khớp nguyên văn.** Xem [REGRESSION_IDS](./REGRESSION_IDS.md) để đối chiếu từng lỗi. Full vẫn FAIL, các test SKIP không thành PASS.

Năm unit workflow/history được cập nhật fake repository để phản ánh việc đọc thread và messages riêng; không hạ assertion nghiệp vụ. Permission contract được sửa bằng cách dùng quyền canonical hiện có, không thêm quyền giả hay nới guard.

## Đo thực tế

- ASGI “Xin chào”: 229,71 ms toàn handler, router 0,55 ms; “Cảm ơn”: 142,39 ms, router 0,15 ms. Cả hai có 0 model / 0 embedding / 0 reranker / 0 retrieval calls.
- Qwen3.5-9b qua provider hiện hành: thanks→môn tự chọn 1925,04 ms; override năm 1478,81 ms; tham chiếu hai ngành 704,11 ms. Mỗi ca đúng 1 router model call, không fallback.
- Mixed Knowledge live: 3620,68 ms đến HTTP 409; 2 ModelOps generate calls, 1 reranker call, 0 embedding. Bộ đếm wrapper retriever bằng 0 không chứng minh không tìm kiếm: evidence path truy xuất bằng adapter riêng. Không dùng số này để tuyên bố Knowledge bỏ qua retrieval.
- UI social/meta quan sát khoảng 181–312 ms ở các lượt mẫu. Không suy p95 hay throughput từ vài mẫu.

## Lệnh và bằng chứng

Từ root, runner `backend/scripts/context_patch_validation.py run` với `--state-file backend/storage/context562/isolation.json --audit-file backend/storage/context562/safety.json --evidence-dir backend/storage/context562/tests`. Labels `red`, `session-red`, `focused-final`, `compatibility-fixed`, `full-final` và `full-verified`; từng `*-run.json` lưu command/cwd/exit, `*.xml` giữ test IDs và nguyên nhân. Hai full run là cần thiết vì full đầu phát hiện lỗi mới; không lặp full cho các sửa frontend sau đó.

Focused gồm ba file `test_hybrid_*`, `test_rag_chat_441`, enumeration/followup, conversation acts, dialogue scope, year488, inference safety498, auth và handoff. Compatibility gồm assistants, workflow history, permission contract và hybrid integration. Ruff scoped các file Context562, receipt `ruff-final.log`.

Từ `frontend`: `node --experimental-strip-types --import ./src/app/auth/test-loader.mjs --test src/services/assistant-chat-route.test.ts src/services/widget-chat.test.ts`; `biome check --line-ending=lf` trên 10 file sửa; `npm run build` gồm `vite build && tsc --noEmit`. Không dùng mock-only test làm E2E PASS.

Bằng chứng private giữ tại `backend/storage/context562`: JUnit/logs, regression comparison, provider/live summaries, source closure probes, UI screenshots, conversation cleanup và source hash seals. Các log nguyên bản không đưa vào Git vì có thể chứa test payload; báo cáo này chỉ ghi metadata cần nghiệm thu.

## Bảo toàn và dọn dẹp

Hash từng bản ghi của 5 collection, 23 binding, 2 source revision và 27 index revision khớp trước/sau. Không reparse, index, approve hay publish, không thay model/config; không restart/deploy/commit/push.

DB test đã drop sau khi đối chiếu ownership và xác nhận không còn. Trang harness widget tạm đã xóa. Bằng chứng kiểm chứng private giữ có chủ ý. Lịch sử chat thử trên trình duyệt có thể còn trong local history để xem lại; DB của các phiên đó đã xóa, capability không hồi sinh được phiên đã xóa.

**CLEANUP_PARTIAL:** kiểm duyệt tự động từ chối lệnh xóa đệ quy runtime với lý do “blocked by policy”. Không retry qua công cụ khác hoặc tắt policy. Thư mục runtime vẫn còn 1185 file/18422741 byte; DB test đã dọn. Đây không phải cleanup PASS.

## Blocker bàn giao

Live Knowledge E2E của DOCX hiện tại còn HTTP 409. Probe cùng hàm đóng gói chứng minh tập đầy đủ đạt closure nhưng tập packed có fact thiếu source row; đây là bằng chứng điều tra tiếp, chưa phải một bản sửa evidence packing hoặc chứng minh duy nhất stack gây lỗi live. Giữ guard, không trả dữ kiện thiếu chứng minh. Toàn bộ chuỗi Knowledge→thanks→followup thật chưa đạt; chỉ phần resolver thật và các đường social/meta được chứng minh riêng.
