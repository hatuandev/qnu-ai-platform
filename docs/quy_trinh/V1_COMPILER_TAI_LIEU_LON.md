# Compiler tài liệu lớn — chia phần, reasoning và chạy song song có giới hạn

## Những gì đã triển khai

### Chia tiếp thích nghi (planner v5)

Lượt mới luôn có ít nhất một checkpoint phần. Projection/prompt v4 giữ nguyên; planner v5 bật refinement đã ghim trong config. Chỉ phản hồi `chat_output_truncated` với raw `finish_reason=length` và có visible content mới được chia tiếp. HTTP422 khác, uncertain, timeout hoặc content rỗng không tự chia/gửi lại. Không suy rằng model output4K luôn đủ.

- Chia phần sở hữu thành hai nhóm tại biên unit, tránh cắt rowspan; giữ header/context cha và output ceiling. Đơn vị nhỏ nhất không vừa trả `compilation_refinement_atomic_limit`.
- Giới hạn ghim: sâu tối đa4, tổng node tối đa31 lần số phần gốc, thời gian1500s cho run. Trước dispatch phải còn đủ queue+deadline inference; không lặp vô hạn. Usage tính cả parent bị cắt và các con.
- Node cha giữ raw lỗi, chỉ completed khi con đủ. Các con có `parent_segment_id`; JSON chứa scope/ID cha/con, Markdown dựng từ JSON và bảng nguồn, không gọi LLM ghép lại. Main JSON chứa `compilation_nodes`, main Markdown liên kết node gốc.
- API progress thêm `nodes`; `GET .../segments/{index}/artifacts/draft_json|markdown` dùng cùng workspace/collection authorization và checksum reader. E2E in node state, deadline tính cả refinement budget.
- Migration0009 thêm liên kết cha và Markdown artifact. Lượt v2/v3/v4 cũ không tự đổi manifest/hash; dữ liệu và lịch sử giữ nguyên.
- Phục hồi E2E cần `--recover`; run đang chạy hoặc đã xuất bản không bị thay. Run uncertain hoặc run cũ chưa xuất bản được tạo lượt mới có idempotency, dùng nguồn OCR đã có.

### Review bảng literal và chạy song song (phiên 751)

Lượt review mới ghim `literal_check_version=1` và `review_concurrency=2` trong trace. Một phần chỉ dùng kiểm tra xác định khi mọi ô sở hữu khớp đúng ID bằng chứng, ID bảng, văn bản, hàng/cột, header và rowspan/colspan; ID trùng hoặc tham chiếu thiếu đều trả về nhánh review bằng model. Kết quả vẫn qua cùng bộ kiểm tra coverage/citation, lưu assessment/checksum và kiểm quyền. Đây là xác nhận giữ nguyên nguồn, **không xác nhận OCR đúng với ảnh**. Narrative, điều kiện, nguồn không phải ô bảng và mọi sai khác vẫn cần model.

Các phần cần model chạy tối đa hai phần đồng thời, mỗi phần có phiên DB riêng. Chờ cả nhóm đang gửi hoàn tất trước khi dừng vì lỗi; không tự gửi lại yêu cầu uncertain. Giới hạn ModelOps chung vẫn áp dụng. Trace cũ không có chính sách này tiếp tục xử lý theo hợp đồng cũ.

Đối chiếu chỉ đọc với PDF điểm sàn đã có: 16/22 phần của lượt review cũ đủ điều kiện kiểm tra literal. Đây không phải số đo thời gian chạy thật của chính sách mới.

Request mới dùng projection `compact/v3` trong scope từng phần: giữ ID, nội dung, loại, trang, hàng/cột, span, header và cờ chất lượng; hash/identity/bbox đầy đủ vẫn nằm ở snapshot và report do backend phân giải. Scope cũ không có projection được dựng lại bằng `full`; `compact/v1` và `compact/v2` cũng giữ đúng schema cũ. Citation ở cấp bảng mở ra các ô của bảng; citation tới ô luôn mang đủ hàng và header. Đây là context bắt buộc; nếu không vừa sẽ báo lỗi, không cắt ô để vừa ngân sách.

`reference_contract_version=2` ghim schema gồm các nhánh object hoàn chỉnh: covered/supported/contradicted phải có nguồn đối chiếu; mỗi nhánh vẫn cần explanation/suggested_action. Không có nguồn cho phép thì không thể chọn supported/contradicted. Thử synthetic với Qwen thật đạt trong 4.1s; đây là kiểm chứng giao thức, không phải nghiệm thu tài liệu thật.

Compiler mặc định lấy `min(COMPILER_MAX_OUTPUT_TOKENS, ceiling ModelOps)` khi người gọi không chỉ định output. Model khai báo 4096 được dùng 4096, Qwen hiện tại vẫn 8192. Nếu người gọi chỉ định 8192 trên model trần 4096 thì trả 422 đúng hợp đồng, không âm thầm thay yêu cầu. Lỗi chung HTTP422 không phải căn cứ chia tiếp.

Planner không trộn phần bảng literal với phần văn xuôi. `--recover` chỉ tạo lại review đã completed theo chính sách cũ nếu chưa xuất bản; giữ review cũ trong lịch sử và dùng key mới. Không thay review running/uncertain bằng nhánh này.

### Nền tảng giữ nguyên

- Giữ snapshot đầy đủ và bất biến. Khi request một lượt vượt giới hạn, lập manifest các phần theo block/hàng bảng; bỏ evidence map và ảnh Base64 khỏi request từng phần. Bảng literal do backend ghép từ nguồn, không nhờ model viết lại ô.
- Mỗi phần có input/schema hash, provider/config, trạng thái, raw response, kết quả dẫn xuất và usage quan sát được. Một phần/hàng không vừa ngân sách sẽ báo lỗi rõ, không tự cắt nguồn.
- Compiler dùng lease/fencing hiện có; lượt in-flight không có raw giữ `uncertain`, không gửi lại mù quáng.
- MD/JSON tổng hợp tạo từ các phần đã xong; mỗi generation có hai blob đã đọc lại kiểm hash và con trỏ DB; bản partial không đi vào publication.
- Review nhiều phần kiểm mỗi source/draft unit đúng một lần, giữ nguồn trích dẫn làm context; report và publication gate giữ nguyên.

### Planner/projection v4 (`qnu.compiler.plan/v4`)

- **Ước lượng nội dung sẽ viết, không phải kích thước nguồn.** `output_content_bytes(max_output_tokens) = tokens × 0.5 × 3` byte; mỗi unit có chi phí viết riêng (`ROW_INTERPRETATION_BYTES` cho hàng bảng, `SECTION_FRAMING_BYTES` cho khung đoạn). Đây là proxy lập kế hoạch; chưa đo lại số phần hoặc tốc độ của PDF thật sau sửa v4.
- **Đóng gói theo 70% capacity input** (`TARGET_RATIO`), dựa trên `request_input_tokens` thật của từng phần sau khi dựng, không dựa trên byte JSON của nguồn.
- **Context có vai trò tường minh**: `table_header`, `caption`, `section_heading`, `document_note`, `neighbour_note`. Giữ toàn bộ đuôi sau bảng cuối, cả khi vượt 6 block/4000 byte; bảng giữa tài liệu giữ cả chú thích/văn bản phía sau đến bảng hoặc tiêu đề kế tiếp. Context này có `scope=unresolved`: chỉ gắn điều kiện cho hàng khi nguồn xác định phạm vi; chưa rõ phải giữ unknown. Nếu không vừa ngân sách thì lỗi rõ, không bỏ chú thích âm thầm.
- **Không tự nối bảng**: hai bảng ở trang kề, cùng header hoặc số cột chưa chứng minh là cùng bảng. V4 không tạo `table_links` từ heuristic này; vẫn giữ bảng/hàng/header riêng và nguồn trích dẫn.
- **Outline gọn** thay cho census từng block: số trang, danh sách bảng (số hàng, số hàng header), tiêu đề, kích thước đuôi ghi chú và cờ `shared_as_context`.
- **Biên chính xác**: `finalize_plans` dựng lại từng phần với tổng thật, nếu `input_tokens > capacity` thì tách đôi nhóm và lặp (tối đa 32 lượt); không tách được thì `compilation_segment_too_large`. Sau đó xác nhận mỗi ref nguồn thuộc đúng một phần.
- Prompt v4 (`qnu.compiler.segment.prompt/v4`) giữ các ràng buộc owned/context, bổ sung phạm vi chú thích chưa xác định và cấm suy nối bảng từ header.

### Tương thích v2/v3

- `compilation/projection.py` và `compilation/units.py` là primitive đóng băng dùng chung; `compilation/segments_v2.py` giữ nguyên hành vi v2 (`qnu.compiler.plan/v2`, `qnu.compiler.segment.prompt/v2`). Test ghim SHA-256 của payload và prompt v2.
- V3 dựng lại layout/prompt cũ khi replay scope đã lưu, kể cả heuristic liên kết và giới hạn context cũ, để giữ input hash. Chỉ lượt mới dùng v4; không sửa snapshot/manifest của lượt cũ.
- `plan_from_scope` thiếu `projection_version` ⇒ đọc là v2; version lạ ⇒ 409 `compilation_segment_version_unsupported`. Phần mới ghi v4 vào scope/config/`request_hash`.

### Reasoning có hợp đồng (`qnu.domains.modelops.reasoning`)

- Chính sách khai báo theo provider trong `extra_config["reasoning_policy_v1"]`: `mode` (`server_default|effort|toggle|chat_template_kwarg`), `parameter`, `low_value`, `off_value`, `tasks`, `verified`, `note`.
- Chỉ áp dụng khi `verified=true` và task nằm trong `compiler`/`compiler_review`. Không suy đoán theo tên model, không hardcode tham số cho mọi endpoint.
- Mặc định `server_default`: không gửi tham số nào, model dùng mặc định server. Nếu chưa xác nhận endpoint chấp nhận, giữ nguyên mặc định và ghi rõ trong trace.
- Trace được lưu ở `run.config["provider"]["reasoning"]`, `segment.config["reasoning"]` và review; resume so sánh chính sách đang áp dụng với chính sách đã ghi, khác nhau ⇒ `compilation_reasoning_changed` / `compilation_review_reasoning_changed`.
- Compiler một lần gọi cũng ghim và truyền `run.config["reasoning_directive"]`. Run cũ chưa ghi directive tiếp tục giữ mặc định, không áp chính sách mới ngầm.
- API: `GET/PUT /modelops/providers/{provider_id}/reasoning` (quyền `ai.models.manage`). Không đổi server/model/API key/.env.

### Chạy song song có giới hạn

- `COMPILER_SEGMENT_CONCURRENCY` mặc định 2, tối đa 4. Chỉ các phần thực sự độc lập mới chạy đồng thời; phần không phụ thuộc kết quả phần khác.
- Mỗi phần mở session riêng, tự kiểm `run.worker_id` trước khi ghi; mất lease ⇒ `claim_lost`, không ghi đè.
- Chỉ orchestrator ghi bản partial (một writer), sau mỗi lần một phần kết thúc.
- Phần lỗi/không chắc chắn dừng việc khởi động phần mới nhưng **không huỷ** phần đang chạy (tránh usage uncertain cho bytes sắp bền vững). Run chỉ `completed` khi mọi phần `completed`.
- Đặt cờ dừng trước khi trả slot; hủy orchestrator hoặc lỗi ghi partial cũng đóng hàng đợi trước khi đợi phần đang chạy kết thúc.
- Usage phần được settle bằng session kế toán riêng; trước khi ghi raw/status/draft vẫn kiểm claim. Mất claim không commit dữ liệu phần qua `usage_service.settle`. Recovery không thay usage đã đo bằng unknown.
- Ghép theo `segment_index`, không theo thứ tự hoàn tất.

### Giới hạn dùng chung cho model

- ModelOps dùng Redis hiện có để chia slot giữa API/worker, workspace và provider alias có cùng endpoint/model trong cùng `CACHE_NAMESPACE`. `MODEL_CHAT_CONCURRENCY` mặc định 4; `MODEL_CHAT_QUEUE_TIMEOUT_SECONDS` mặc định 300. Đây là chính sách vận hành, không phải capacity suy ra từ `/models` hoặc `max_num_seqs`.
- Các process cùng deployment cần dùng chung Redis/namespace/cấu hình giới hạn. Mỗi run compiler vẫn tối đa 2 phần mặc định, đồng thời chịu mức trần chung. Chat và review dùng cùng cổng admission.
- Hết thời gian xếp hàng hoặc Redis lỗi: không gửi request upstream, báo `chat_admission_timeout`/`chat_admission_unavailable`, usage biết chắc bằng 0. Thời gian xếp hàng tách khỏi deadline inference.
- Hủy/lỗi không chắc chắn giữ slot đến TTL (`request timeout + 30s`); không gọi lại tự động. Đây là lease phía QNU, không chứng minh server đã hủy tác vụ; server vẫn phải quản lý giới hạn thực của nó. Lỗi trả slot giữ TTL, không làm mất phản hồi đã đo.

### Tiến độ

- `GET .../compilation-runs/{id}/progress` thêm `queue_timeout_seconds`, cùng các bộ đếm/trạng thái thật và thời lượng từng phần.
- E2E in một dòng khi trạng thái đổi (không in mỗi lần poll), và tạo run mới khi lượt trước do planner cũ lập.
- Ngân sách chờ E2E: `ceil(total / effective_concurrency) × (perPartMs + queueMs) + 60000`, ít nhất 240s; một phần vẫn có đủ một deadline model. Đây là hạn chờ tối đa; hoàn tất/lỗi được trả ngay lúc poll quan sát được.

## Giới hạn minh bạch

Input vẫn dùng cận trên byte UTF-8 (chưa phải tokenizer model); output dùng proxy lập kế hoạch. Proxy không bảo đảm model luôn kết thúc trong ngân sách, và chưa có số đo tốc độ thật khi chạy song song — `max_num_seqs=8` của vLLM không có nghĩa là nhanh gấp 8 hay dành 8 slot cho compiler.

Chỉ tái sử dụng phần đã lưu trong cùng run/snapshot và cùng cấu hình. Nguồn/revision thay đổi tạo run mới; chưa tái dùng cache xuyên revision. Review semantic vẫn có thể báo thiếu/nghi ngờ; coverage ID không chứng minh nội dung đúng.

Chưa có màn hình giao diện riêng; API progress và bản partial cung cấp trạng thái thật. Review POST vẫn thực thi đồng bộ; client cần đủ thời gian cho nhiều phần. Chưa áp dụng migration mới (không cần cho thay đổi này) và chưa chạy nghiệm thu.

## Áp dụng vào phiên đang dở

Khi lượt đang chạy đã kết thúc, khởi động lại đúng cửa sổ serve để nạp mã mới (không tự restart trong phiên sửa này):

```powershell
.\test-v1-e2e.ps1 serve
```

Serve chạy `alembic upgrade head` theo cơ chế hiện có. Không cleanup/init nếu đang tiếp tục phiên chưa purge. Chờ sẵn sàng rồi ở cửa sổ thứ hai:

```powershell
.\test-v1-e2e.ps1 run admissions-compilation --headed
.\test-v1-e2e.ps1 run admissions-publication --headed
.\test-v1-e2e.ps1 run admissions-chat --headed
```

Chỉ chạy tiếp sau PASS.

Run v2/v3/v4 vẫn dùng scope đã lưu. Để tạo lượt v5 từ nguồn OCR cũ khi lượt terminal không thể tiếp tục, chạy `run admissions-compilation --recover`. Helper giữ lịch sử, không sửa phần uncertain thành pending, không thay run đang chạy hoặc đã xuất bản.

Nếu muốn tận dụng reasoning đã tắt, khai báo chính sách trước khi chạy:

```powershell
# chỉ khi đã xác nhận endpoint chấp nhận tham số này
$body = @{
  policy = @{
    mode      = "chat_template_kwarg"   # hoặc effort | toggle
    parameter = "enable_thinking"
    off_value = $false
    tasks     = @{ off = @("compiler", "compiler_review") }
    verified  = $true
    note      = "probe ngày ... xác nhận endpoint nhận chat_template_kwargs"
  }
} | ConvertTo-Json -Depth 5
Invoke-RestMethod -Method Put -Uri "$api/modelops/providers/$providerId/reasoning" `
  -Headers @{ Authorization = "Bearer $token" } -ContentType "application/json" -Body $body
```

`tasks` ánh xạ **mức → danh sách tác vụ** (`off`/`low`), không phải tác vụ → mức. Không đặt `verified=true` khi chưa thử với chính endpoint đó: nếu sai, request có thể bị từ chối thay vì chạy mặc định.

## Lệnh kiểm chứng dành cho người dùng

Các lệnh dưới đây là nhóm kiểm tra theo phạm vi. Kết quả thực chạy của phiên 751 được ghi trong [nhật ký](../nhat_ky/2026-10-30_phien_751_compiler_refinement.md); không suy kết quả cho lệnh khác. Unit từ repo root:

```powershell
Push-Location backendV1
.\.venv\Scripts\python.exe -m pytest tests/unit/test_compiler_projection_746.py tests/unit/test_compiler_parallel_746.py tests/unit/test_compiler_fixes_747.py tests/unit/test_model_chat_admission_747.py tests/unit/test_modelops_reasoning_746.py tests/unit/test_compilation_segments_744.py tests/unit/test_compilation_review_parts_744.py tests/unit/test_compilation_fencing_744.py
Pop-Location
```

Integration cần DB/cache test theo cấu hình quy định, không dùng DB phục vụ:

```powershell
Push-Location backendV1
.\.venv\Scripts\python.exe -m pytest tests/integration/test_compiler_segments_api_744.py tests/integration/test_compiler_review_652.py tests/integration/test_compiler_queue_645.py tests/integration/test_compiler_edits_654.py tests/integration/test_publication_646.py
Pop-Location
```

Kiểm tra frontend (khi cần):

```powershell
Push-Location frontendV1
npx vitest run tests/progress-budget.test.ts
npx tsc --noEmit
npx biome check e2e/stages
Pop-Location
```

Không coi thiếu môi trường hoặc NOT RUN là PASS. Gate rộng lịch sử còn lỗi vẫn giữ FAIL cho đến khi được kiểm chứng lại.

Test admission ở trên dùng mock Redis: chưa chứng minh Lua atomicity giữa process hoặc giới hạn dưới tải thật. Cần kiểm chứng Redis cô lập và E2E nhiều job trước nghiệm thu; không dùng DB/cache phục vụ để chạy test tích hợp.
