# Phiên 416 — Đợt 1: readiness, reranker server AI và vòng đời workflow

## Phạm vi và quyết định

Người dùng đồng ý triển khai đợt 1 của đề xuất phiên 415, yêu cầu reranker lấy từ server AI QNU. Áp dụng các skill Backend, Frontend/admin-design, clean-code, chatbot-builder, ModelOps và RAG để giữ cấu hình động, scope và chốt đối soát. Không reset DB/Redis, không OCR lại, không nạp lại vector, không tự xuất bản trợ lý/workflow hoặc kho. Không triển khai đợt 2 về evidence prose, mùa/đợt tuyển sinh hay chất lượng nội dung 82 câu.

## Thay đổi

### Readiness theo snapshot đang phục vụ

- `assistants/knowledge_readiness.py` dùng chính `HybridRetriever.resolve_retrieval_snapshot`, scope tenant/workspace của collection; chỉ đếm binding/index đang active trong generation đang phục vụ. Kiểm tra chunk count, parity, nguồn revision-bound ready và structured review.
- Draft chưa xuất bản không bắt buộc phải nạp/duyệt hết. Legacy document chỉ được đếm nếu thật sự là kho legacy không có binding/generation; phải indexed và active. Không dùng số document/chunk metadata cũ làm bằng chứng.
- `assistants/readiness.py` fail-closed khi mất DB, collection không tồn tại hoặc khác tenant; bỏ đường seed giả làm readiness có thể xuất bản.
- `assistants/model_readiness.py` đối soát provider/model/role/key từ DB, không gọi LLM tốn phí ở mỗi GET. Khóa relational là nguồn có thẩm quyền: không dùng JSON/key cũ để che giấu trạng thái disabled/invalid/quota exhausted. Cặp không pin phải phân giải catalog duy nhất; không tự chọn một provider khi alias trùng.
- Đây là kiểm tra cấu hình/nguồn đã xuất bản, không phải cam kết dịch vụ upstream luôn khỏe hoặc chatbot đạt chất lượng học thuật.

### Cặp provider–model không bị mất khi lưu

- AssistantModelPolicy, AskRequest và LLMGenerateRequest có primary `preferred_provider_id` và `fallback_provider_id`; chuyển tiếp qua RAG, DAG RAG/LLM/rewrite/router/drafting và consulting dispatcher.
- AssistantRerankerPolicy mặc định provider/model `null`, lấy defaults ModelOps DB; bỏ mặc định Cloudflare/model cứng trong schema và form save.
- FE thêm kiểu provider/model, options theo catalog/role, giữ cả alias trùng trên hai provider, giữ hiển thị cấu hình đã lưu nếu catalog không còn model. Dùng Select/Field có sẵn; không tạo primitives mới.
- `policy-update.ts` giữ toàn bộ knowledge/reranker policy khi sửa chat, lưu provider và tên model nguyên vẹn; threshold 0 không bị ép lại 0.4.
- Provider API công khai model_specs và supports_chat, không lộ khóa. Không đưa PaddleOCR-only vào danh sách chat.

### Chat chỉ failover theo policy

- `modelops/services/chat_routes.py` tạo danh sách cặp primary/fallback. Alias không pin cần catalog exact; provider pin có thể nhận alias mới chưa liệt kê, nếu không có metadata cấm role chat. Không đoán họ model bằng tên/keyword.
- Không gửi alias 9router lên mọi endpoint custom/vLLM. Hai model cùng provider vẫn có hai route riêng; không âm thầm thay bằng model mặc định ngoài policy.
- Cả generate và streaming dùng một planner, giữ tên requested/served, usage và lỗi thực đã sửa ở phiên 414. LLM node ưu tiên policy trợ lý hơn cấu hình node.

### Workflow terminal audit và phục hồi

- `workflows/service.py` cấp ID trước flush; bao setup/flush/commit, engine và finalize. Lưu running trước engine; deadline `WorkflowDagSpec.timeout_seconds` cấu hình được (1–3600s, mặc định 300s), lưu execution_deadline vào runtime snapshot.
- Lỗi/cancel/timeout: rollback session hiện tại, session sạch upsert failed/cancelled, correlation, failure_stage/code và completed_at. Cleanup có giới hạn thời gian và shield cancellation; vẫn ghi bằng session sạch nếu rollback hỏng. Log stack frame không kèm giá trị secret upstream.
- `workflows/execution_audit.py` chỉ đổi record running; không ghi đè terminal đã hoàn tất. Worker `workflow_recovery.py` đối soát deadline mỗi 30s, chừa 30s cho finalization; không replay tool hoặc side effect.
- Record cũ không có deadline không bị suy đoán/xóa; paused_for_approval không bị cron hết hạn theo deadline chạy. Resume HITL không được mở rộng/refactor trong đợt này. DB hoàn toàn không truy cập được thì audit có thể không ghi được ngay; lỗi được log và deadline mới cho phép reconcile khi DB phục hồi.
- Worker đang chạy phải khởi động lại để nhận cron mới; không tự restart trong phiên vì tránh ngắt job người dùng.

## Cấu hình thật đã lưu theo yêu cầu

Qua PATCH assistant, giữ nguyên các policy khác:

- Primary: `prov_20261013041934` / `gh/gpt-6-luna[1m]`, endpoint 9router local đang cấu hình.
- Fallback: `prov_gemini` / `gemini-3.1-flash-lite`.
- Reranker: `prov_rtx5090_vllm` / `bge-reranker-v2-m3`, `http://100.105.13.53:8000/v1`, top_k5 / threshold0.4. Model/provider này là cấu hình DB và thao tác setup, không hardcode vào runtime nghiệp vụ. Defaults ModelOps đã trỏ server này nên không cần đổi defaults toàn hệ thống.

## Kiểm chứng

- Test trọng tâm có PostgreSQL thật: 96 passed. Fixture một nguồn published + một draft đếm đúng1 khi legacy documents0; parity false bị chặn. Engine exception ghi failed/completed_at thật sau rollback, deadline cron đóng running nhưng không đóng paused. Outer transaction rollback toàn bộ dữ liệu test.
- Bộ lỗi/cancel/timeout/setup/finalize/rollback/role/key và worker: 19 passed trước ca bổ sung khóa disabled; 13 test phase1 cuối đạt. HTTP MockTransport dùng adapter sản xuất với credential fixture không kích hoạt mock adapter; primary HTTP503 → chỉ backup đã chọn, cả JSON/SSE, không gọi server encoder, served model/usage đúng.
- FE: 3 regression tests đạt; scoped Biome9files đạt; Vite + TypeScript build đạt. Không quét/sửa lint toàn FE ngoài scope.
- Ruff toàn Backend đạt (cảnh báo Access denied ở thư mục temp cũ vẫn tồn tại). Final Pytest: **1041 passed, 11 failed, 5 skipped**, 107.53s. Cả11 failure trùng baseline phiên414/415: cutover2, decommission3, e2e_canary1, rag_reconciliation1, auth_cookie1, universal_tools1, consulting_dispatcher2. Không coi là đạt toàn suite. Test worker count1cron cũ được cập nhật thành kiểm tra2coroutine theo contract mới; không còn failure mới trong final run.
- Live: reranker trực tiếp không qua wrapper degradation trả điểm0.998266 cho đoạn lịch xét tuyển, 0.008554 cho điểm chuẩn, 0.000016 cho thời tiết. Đây là kiểm chứng endpoint/contract, không phải benchmark RAG.
- Readiness thật có19 nguồn / epoch3, score93, ready_for_publish=true, blockers=[]; còn warning chưa Ragas TM-08.
- Chat API200, trả1800.55.88.49 có citations; usage thật `custom` / `gpt-6-luna`, fallback=false; workflow `5c6a230e-dd70-425a-8b14-6db9b1e3ebd6` completed6nodes. Không lấy một câu smoke làm chứng nhận đúng cả bộ82.
- Artifacts: `backend/storage/phase1_416_live.json`, `phase1_416_live_final.log`, `pytest416_focus3.log`, `pytest416_failurepaths2.log`, `pytest416_keyauthority.log`, `pytest416_finalgate.log`, `ruff416_verified.log`; `frontend/build416_finalgate.log`.

Final full-suite có log callback Windows Proactor sau event-loop teardown; đây không tạo failure mới và chưa xử lý trong đợt1. Không sửa các bộ publish/auth/export/reconciliation ngoài scope chỉ để làm xanh test. Test PostgreSQL opt-in đã chạy riêng và đạt; mặc định full suite skip fixture này.

## Các tệp và bài học

Thay đổi tập trung: assistant schemas/readiness +2helpers; modelops schemas/provider_service/inference_service +chat_routes; rag schemas/service; consulting_dispatcher; workflow service/schemas +execution_audit và5node handlers; ARQ config +workflow_recovery. FE detail/types/model/knowledge sections +model-options/policy-update vàtests. Tests điều chỉnh contract readiness, dynamic provider pin, worker cron và provider safety; thêm phase1 unit/PostgreSQL suites.

JSON policy là dữ liệu nghiệp vụ cần round-trip nguyên vẹn, không dựng lại một phần rồi để schema gán mặc định. Publication readiness phải xét snapshot serving, không đếm staging hay legacy table. Terminal audit cần transaction độc lập vì các adapter/key services có thể commit session giữa workflow; khi đọc lại trong cùng identity map sau update session khác phải refresh để đối soát DB thật.
