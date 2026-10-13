# Phiên 413 Chẩn đoán ModelOps 9router và đề xuất xử lý

## Mục tiêu

Người dùng cập nhật model chatbot tuyển sinh, yêu cầu đánh giá vấn đề và đề xuất. Trong lúc chẩn đoán, người dùng đổi provider qnu-9router từ địa chỉ public sang `http://localhost:20128/v1`, cung cấp ảnh lỗi test model trên `/models` và yêu cầu kiểm tra. Phiên này chỉ chẩn đoán/probe, chưa sửa runtime, chưa tái xuất bản.

## Kết luận trọng tâm

9router local kết nối được và cả hai alias model hợp lệ. Chức năng test model của QNU gửi payload không hợp lệ; runtime chatbot còn có hai lỗi tương thích độc lập. Không cần reset DB/Redis, xóa model, tắt API-key requirement hoặc bật tunnel để khắc phục lỗi được quan sát.

## Bằng chứng thực tế

Provider `prov_20261013041934`, type custom, hiện dùng `http://localhost:20128/v1`; URL resolver giữ nguyên. GET `/v1/models` có khóa từ DB trả HTTP 200 và 552 model IDs, chứa cả `gh/gpt-5.4-mini` và `gh/gpt-6-luna[1m]`. Không hiển thị hoặc lưu khóa vào artifacts.

API đúng nút Test tất cả `/platform/v1alpha1/modelops/providers/{id}/models/test` trả HTTP 200 cho API quản trị nhưng hai kết quả nội bộ `error`, upstream HTTP 400. Code `_ping_single_model` tại `backend/app/modules/modelops/services/provider_service.py` gửi chat probe `max_tokens=1` (nhánh reasoning=10), không đủ minimum của upstream.

Ma trận probe trực tiếp local: bỏ temperature, explicit stream=false, giữ nguyên tên model và khóa.

| Model gửi nguyên vẹn | Hạn mức | HTTP | Kết quả |
| --- | ---: | ---: | --- |
| gh/gpt-5.4-mini | 1 | 400 | Invalid max_output_tokens, expected >=16, got 1 |
| gh/gpt-5.4-mini | 32 | 200 | OK; response_model gpt-5.4-mini |
| gh/gpt-6-luna[1m] | 1 | 400 | Invalid max_output_tokens, expected >=16, got 1 |
| gh/gpt-6-luna[1m] | 32 | 200 | OK; response_model gpt-6-luna |

`32` là payload đối chứng của lần chẩn đoán, không phải đề xuất hardcode hạn mức cho mọi model. Alias request giữ nguyên; response model do gateway trả khác alias là bình thường và phải lưu riêng với requested model.

### Tương thích runtime chatbot

Trước khi đổi sang local, adapter thật với provider qnu-9router và primary gh/gpt-5.4-mini trả upstream HTTP 400: `Unsupported parameter: 'temperature' is not supported with this model.` OpenAIAdapter.generate hiện luôn gửi temperature và không đặt stream=false.

Hai probe đối chứng trên endpoint public cũ đã xác minh:

- Bỏ temperature, không chỉ định stream: HTTP 200 nhưng Content-Type text/event-stream, các `chat.completion.chunk`, kết thúc `[DONE]`. Gọi response.json sẽ lỗi.
- Bỏ temperature và chỉ định stream=false: HTTP 200 application/json, answer OK, response model gpt-5.4-mini.

Do đó chỉ tăng token test sẽ chưa sửa được runtime; chỉ hạ temperature xuống 0 cũng không đúng vì upstream từ chối sự hiện diện của tham số đó.

Sau cập nhật config primary gh/gpt-5.4-mini, fallback gemini-3.1-flash-lite, temp0.2/max4000, probe chatbot vẫn có 6 inference successes dùng Cloudflare Llama3.1-8b fallback. Aggregate qnu_workflow ghi tên gh/gpt-5.4-mini theo cấu hình, không phải inference thành công của model này. Gemini hiện active nhưng legacy key rỗng, JSON pool0, relational keys0: dự phòng Gemini chưa có credential sử dụng được.

Batch đầu 4 câu: 1HTTP500/corr_9de8b577196d, 1ReadError, 2HTTP200 nhưng model thật vẫn Llama. Retry tuần tự 5 câu sau lease expiry đều HTTP200: mã trường/quota/sàn vẫn no-answer, GDMN/GDTC còn sai/trộn nguồn cũ; 4 inference calls lại dùng Cloudflare, quota là deterministic gate không gọi LLM. Custom key events ghi provider_request_failed; một workflow của lỗi500 còn running. Chưa có terminal log/stack trace của API cho lỗi500 nên chưa khẳng định căn nguyên; không lấy lỗi này làm bằng chứng model hỏng. Dừng full82 retest vì chưa thực sự đánh giá model mới.

## Các lỗi liên quan đã đọc code và đối soát

1. Readiness trợ lý báo ready_documents0/score78/blocker. `_check_knowledge` đếm `KnowledgeDocument` legacy, trong khi RAG snapshot có19 binding/index/source đang phục vụ, epoch3/genvg_21324678abcf. Đề xuất dùng cùng published snapshot scope với retrieval, không bắt mọi nguồn chưa xuất bản phải ready.
2. Model readiness chỉ kiểm tra primary/fallback strings khác nhau và temperature; chưa kiểm tra provider/credential/capability/health đã xác minh. Vì vậy model policy vẫn passed dù primary request sai và fallback không có khóa.
3. FE `assistant-detail-page.tsx` dựng mới reranker_policy lúc lưu nhưng không giữ provider_id. BE AssistantRerankerPolicy điền default prov_cloudflare. Cấu hình trước là bge-reranker-v2-m3/prov_rtx5090_vllm, sau lưu thành bge-reranker-v2-m3/prov_cloudflare. Đây là mất field/default injection, KHÔNG phải FE viết literal provider_id=Cloudflare. Provider catalogue Cloudflare chỉ có @cf/baai/bge-reranker-base, model bge-reranker-v2-m3 thuộc catalogue server QNU. Chưa probe riêng reranker endpoint trong phiên này.
4. Model policy chưa có persisted primary/fallback provider IDs; runtime suy provider từ model name. Nên lưu tuple provider/model để ngăn nhầm endpoint và tôn trọng tên alias hoàn toàn.
5. `get_active_providers` trả latency_ms110/failure_rate0 tĩnh; con số110ms trên header không phải bằng chứng kiểm tra thật. Không dùng nó để kết luận provider khỏe.
6. Các vấn đề RAG ở phiên412 chưa biến mất do đổi tên model: quota5.173 ở prose không đi qua typed-fact gate; citation thiếu bị DAG chặn; kiểm chứng từ/số chưa chứng minh năm/phương thức/đợt/phủ định; thiếu nguồn thông báo bổ sung. Chưa sửa trong phiên này.

## Đề xuất theo thứ tự

### Ưu tiên 1 Hợp đồng request và probe thống nhất

Dùng chung bộ tạo request theo capability cho test và runtime, nhưng probe gọi đúng provider/model đã chọn và không tự fallback: model A test không được đạt nhờ model B.

Capabilities quản lý ở ModelOps DB theo provider/model gồm supported parameters, tên tham số token, minimum/maximum output tokens và response modes. Không nhánh hardcode tên gh/gpt hay whitelist từ vựng model. Có thể lưu kết quả capability probe thật hoặc override rõ ràng được người quản trị xác nhận; capabilities không rõ thì báo chưa xác minh thay vì âm thầm bỏ tham số.

Chat probe chọn ngân sách thỏa các bounds đã biết thay vì 1 token; budget hữu hạn. Generate đặt stream=false, stream đặt true; validate Content-Type và schema, HTTP200 chưa đủ để coi là thành công. Khi gateway trả sai mode thì báo lỗi protocol cụ thể hoặc gom SSE qua parser chuẩn có giới hạn, không json.loads vô điều kiện.

Temperature chỉ gửi khi model capability hỗ trợ; UI vô hiệu hóa/giải thích trường không áp dụng. Sai tham số là configuration/capability error, không tự đánh model nonexistent hoặc invalid key. Không tự thay tên alias. Bỏ shortcut giả healthy trong production của health probes; thiếu credentials phải báo lỗi thật.

### Ưu tiên 2 Định tuyến và quan sát đúng

Persist primary_provider_id/fallback_provider_id và model alias, chuyển đầy đủ qua assistant profile → DAG → ModelOps. Failover chỉ theo policy đã cấu hình; hiển thị requested model, served model/provider, reason/HTTPcode riêng. Aggregate workflow log không giả làm inference hoặc tính thêm chi phí ước lượng như một lượt model thật. Gemini thiếu khóa phải có warning actionable; không yêu cầu gửi khóa trong chat.

Probe errors giữ upstream code/parameter/bounds có lọc bí mật và không cắt trước thông tin quan trọng như hiện tại120 ký tự. FE phân biệt lỗi payload, khóa, mạng, rate-limit, model unavailable; số đo latency phải từ probe có timestamp hoặc ghi chưa kiểm tra.

### Ưu tiên 3 Readiness và bảo toàn cấu hình

Readiness dùng published retrieval snapshot theo tenant/workspace/generation, source/index parity/review, có nguồn đang serving là đúng với partial publication. Model check dựa vào provider/key/capability và health record gắn fingerprint cấu hình, không gọi LLM tốn phí trong mỗi GET readiness.

FE bảo toàn toàn bộ reranker policy khi chỉ sửa chat model; lựa chọn provider/model là một tuple. Regression round-trip đảm bảo provider_id không bị BE default thay thế. Không tự tái xuất bản trợ lý để né gate.

### Ưu tiên 4 Kiểm chứng lại RAG

Sau khi xác nhận requests thật dùng model mới, thử trước các câu critical ở phiên412, rồi full82. Bổ sung evidence prose cho số liệu với tuple đối tượng/thuộc tính/giá trị/năm/phương thức/đợt/đơn vị/source-page. Đồng bộ citations và kiểm chứng claim/phủ định; không tắt guard. Thiếu năm hỏi rõ hoặc nêu năm sử dụng; chưa đủ nguồn đúng đợt thì từ chối có căn cứ, không lấy phí/điểm/lịch khác thay thế. Bổ sung thông báo chuyên đề qua duyệt/xuất bản như nguồn mới, giữ bộ FAQ evaluation tách biệt để tránh test leakage.

## Tiêu chí nghiệm thu đề xuất

- Cả hai model của 9router local test đạt qua API QNU và actual runtime; đối soát requested alias/served model rõ ràng, không nhờ Cloudflare fallback.
- Generic regression cho min-token, unsupported temperature, JSON/SSE, non-JSON error, 401/429/5xx/timeouts; không khóa test vào tên model cụ thể.
- Không thay nhầm reranker provider sau lưu chat model; readiness nhìn thấy đúng19 nguồn đang phục vụ và giữ partial publication.
- Chạy lại82Q&A, tách accuracy/content từ status answered; các câu critical không sai năm/đợt/phủ định; guard hợp lệ, no-answer đúng khi thiếu chứng cứ.

## Tệp và dữ liệu phiên này

- `backend/storage/admissions_eval413.json`, `admissions_eval413_audit.json`: batch4 và model audit.
- `backend/storage/admissions_eval413_retry.json`, `admissions_eval413_retry_audit.json`: retry5 và key events/model audit.
- `backend/storage/admissions_eval413_primary_probe.json`, `admissions_eval413_primary_stream_probe.json`: đối chứng JSON/SSE gateway public cũ.
- `backend/storage/modelops_local413.json`, `modelops_local413_matrix.json`: catalogue/đúng API test và ma trận direct local.
- Chỉ tạo journal và cập nhật README/PROJECT_CONTEXT/WORK_LOG. Không đổi source code runtime, DB schema, provider config, model list, khóa, source publication, Redis/cache; các probe/chat sinh normal usage/conversation/workflow/key events. Không chạy Ruff/Pytest/Vite vì chỉ đọc code, probe thật và ghi docs; không triển khai fix.

## Bài học

Catalog có model, ping endpoint200 và tên model trong UI chưa chứng minh inference thật. Kiểm tra sức khỏe phải dùng payload hợp lệ cho model đó, validate response protocol, và chia sẻ contract với runtime; không gộp lỗi tham số vào lỗi model/khóa.
