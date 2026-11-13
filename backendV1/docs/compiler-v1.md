# Compiler v1 — OCR thành bản nháp có dẫn nguồn

[Review ngữ nghĩa sau Compiler](compiler-review.md) đối chiếu nguồn đã ghim với
bản nháp, trả báo cáo bỏ sót/sai diễn giải có nguyên văn. [Workflow654](compiler-workflow.md)
nối phiên bản hậu OCR, mặc định tạo review tự động và lưu sửa thủ công thành run
con bất biến để review riêng. Report không tự sửa hoặc phê duyệt draft.

Sau Compiler, [quản lý phiên bản và xuất bản](compiled-publication.md) đăng ký
output bất biến vào document, duyệt và publish bằng quyết định riêng. Các giới
hạn "chưa publication" bên dưới mô tả phạm vi của riêng batch Compiler645.

Luồng BE: chọn kết quả OCR đã hoàn tất → tạo job bền vững → gọi LLM qua ModelOps
→ giữ raw response → kiểm schema/citation → lưu JSON/Markdown bản nháp → đọc qua API.

## Phạm vi

- Chỉ làm việc trong một workspace/collection đã kiểm quyền. Workspace là biên giới
  quyền của `backendV1/`, theo ngoại lệ AGENTS.md; không áp dụng sang `backend/`.
- Một yêu cầu nhận 1–20 OCR run đã hoàn tất thuộc collection. Mỗi nguồn được ghim
  revision, generation, canonical hash, manifest hash và source hash. Không tự lấy
  revision mới nhất hoặc mở rộng sang collection khác.
- Chat hiện hỗ trợ provider `openai_compatible`/`local`. Endpoint, model, credential,
  capability và quota giải quyết qua ModelOps DB. Không có LLM API key trong
  `.env`, không fallback hoặc retry HTTP âm thầm.
- Kết quả luôn là `publication_status=draft`, `requires_review=true`. Kiểm schema
  và citation không thay thế đánh giá tính đúng của phần diễn giải.

## Chuẩn bị ModelOps

Sau khi cấu hình môi trường v1 và áp migration trên DB được phép, dùng các API
ModelOps hiện có để tạo provider có capability `chat`, thêm credential mã hóa,
cấp provider cho workspace, chọn default chat và cấu hình quota tháng UTC.
Schema Compiler/OCR đã nằm trong `0001_initial_schema`; xem [migration](migrations.md).
Đợt triển khai chỉ migrate DB test; DB phục vụ chưa được thay đổi.

Với 9router, dùng `base_url=http://localhost:20128/v1`, model `gh/gpt-6-luna` như
người dùng chỉ định. Đây là lựa chọn cấu hình, không phải model hardcode trong
Compiler. Gateway hiện công bố context 1.050.000 và max completion 128.000 token;
giới hạn khai báo không chứng minh model luôn đạt được các mức đó.

`token_limits` phải gắn đúng endpoint/model. Đổi endpoint/model làm capacity cũ
stale; phải cấu hình lại. Không tự đánh dấu provider đã được kiểm định từ danh mục.
Endpoint private chỉ được runtime cho phép ở môi trường không phải production,
theo chính sách server hiện có; body Compiler không được nhận URL/secret.

## API

Tiền tố: `/platform/v1alpha1/workspaces/{workspace_id}/collections/{collection_id}/compilation-runs`.

Luồng một tài liệu từ FE dùng `selective_supplement=true`, `auto_review=false` và
`text_versions` ghim bản đã lưu. Bản v0 được biểu diễn bằng cách không khai báo
entry của run trong `text_versions`. Model/output bỏ trống để ModelOps giải quyết.
Không gửi `source_first` hoặc `ai_supplement` cùng chế độ này.

Worker giữ toàn bộ bản nền từ nguồn, chỉ gọi AI cho nhóm cần bổ sung. Gợi ý nằm
trong `supplement`, tách khỏi bản nền; metadata cần người dùng xác nhận khi đăng ký.
`supplement.state` phân biệt `running`, `completed`, `skipped` và `incomplete`.
`GET /{run_id}/draft?partial=true&group_by_source=true` đọc bản xem trước có nhóm;
404 `compilation_partial_not_found` nghĩa là chưa có bản xem trước, không phải lỗi
nguồn. Bản xem trước không được đăng ký. Khi AI tùy chọn lỗi, bản hoàn tất vẫn giữ
nguồn đầy đủ, báo `failure_code`/`planning_error` và `incomplete_groups` riêng.
Lỗi source hash, quyền, storage hoặc đổi cấu hình đã ghim không được bỏ qua.

| Phương thức | Đường dẫn sau tiền tố | Mục đích |
|---|---|---|
| POST | rỗng | Tạo job; bắt buộc `Idempotency-Key` |
| GET | rỗng | Danh sách theo generation giảm dần, `limit=1..100` |
| GET | `/{run_id}` | Trạng thái, mã lỗi, thời gian, usage quan sát |
| GET | `/{run_id}/draft` | JSON bản nháp đã hoàn tất |
| GET | `/{run_id}/markdown` | Markdown dẫn xuất, bảng nguồn giữ span |
| GET | `/{run_id}/raw` | Nguyên bytes provider trả về, kể cả run failed |

Body tạo job:

```json
{
  "topic": "Chỉ tiêu tuyển sinh",
  "ocr_run_ids": ["ocr_<id_da_hoan_tat>"],
  "provider_id": "prv_<chat_da_duoc_cap>",
  "max_output_tokens": 8192
}
```

`provider_id` bỏ trống thì chọn default chat của workspace. `max_output_tokens`
bỏ trống thì ModelOps tự chọn theo model và context còn lại; không có trần cấu
hình môi trường nào được áp. Planner chia theo cấu trúc khi tài liệu cần nhiều
request, giữ nguồn và kết quả từng phần. Lỗi token xác định được chỉ chia lại
phần lỗi. Xem [luồng tài liệu lớn](../../docs/quy_trinh/V1_COMPILER_TAI_LIEU_LON.md).

POST mới trả 201 với `{run, created, dispatched}`. Cùng actor/workspace/key và
nội dung trả 200 cùng run; key trùng nhưng nội dung khác trả 409. Key mới là yêu
cầu mới, có thể gọi model lần nữa. Queue lỗi vẫn giữ run `queued`, reconcile sau.

Admin/editor được tạo; admin/editor/reviewer/member đọc trong workspace có quyền.
Worker kiểm lại membership/role/workspace trước khi đọc nguồn và gọi model. ID
của run ở kho/workspace khác trả 404. Thu hồi quyền sau khi tạo job chặn thực thi.

## Trạng thái và phục hồi

`queued → running → completed | failed | uncertain`.

- Dùng ARQ/queue/lifecycle v1 hiện có, thêm `compile_run` và
  `compilation_reconcile`; không thêm framework hoặc worker hệ thống mới.
- Claim nguyên tử, lease + heartbeat và fence ở DB. Worker cũ không được commit
  hoặc gửi request mới sau khi mất quyền sở hữu.
- Lưu `request_started_at` trước HTTP. Worker mất giữa request mà chưa giữ raw
  thì run thành `uncertain`, không tự gửi lại. Timeout lúc đọc/ghi có cùng nguyên tắc.
- Có raw hợp lệ đã lưu thì phục hồi xử lý nội bộ từ raw, không gọi LLM lần nữa.
- Reconcile mỗi 5 phút tìm queued thiếu delivery/cũ và running hết lease.
  `OWN_RECONCILE` là công tắc vận hành hiện hữu.
- Provider/prompt thay đổi sau lúc tạo job chặn lượt chạy, không lặng lẽ đổi model.
- Schema sai, citation ngoài tập nguồn, output bị cắt hoặc provider lỗi không
  tạo bản nháp completed. Raw provider vẫn được giữ qua BlobStore.

## Dữ liệu và bảo toàn bằng chứng

Ba bảng mới: `kb_compilation_runs`, `kb_compilation_inputs`,
`kb_compilation_artifacts`. FK tổ hợp giữ đúng workspace/collection giữa Compiler
và OCR. Migration thêm unique scope cho OCR; không sửa migration cũ. Downgrade
từ chối để tránh xóa bản nháp/bằng chứng âm thầm.

Artifact content-addressed: `input_snapshot`, `raw_response`, `draft_json`,
`markdown`. Ghi lại khác bytes cho cùng kind bị chặn; đọc kiểm cả size và SHA256.
Read API trả ETag và private/no-store, raw octet-stream có nosniff.

LLM chỉ tạo title/sections/paragraphs/citations/unknowns theo schema. Citation ID
có dạng `{ocr_run_id}:{evidence_id}`. Server đối chiếu ID với nguồn đã ghim và
đính kèm mapping tới revision/page/block/cell cùng hash. Chỉ citation có thật
chưa bảo đảm câu diễn giải đúng — trường `semantic_faithfulness=not_evaluated`
ghi giới hạn đó.

Bảng được server sao chép nguyên từ canonical OCR vào `source_tables`, giữ các
ô rỗng, `0`, dấu gạch, header, rowspan/colspan, footnote trong bằng chứng nguồn.
Không dùng LLM dựng lại bảng hoặc ghi đè OCR gốc. Chưa có duyệt/xuất bản/index/RAG.

## Ngân sách và usage

Đầu vào text dùng cận vận hành bảo thủ: số byte UTF-8 của messages đã serialize
+ 64 token/message + 128 token request framing. Đây không phải tokenizer đo chính
xác, không bao gồm chi tiết prompt ẩn do gateway chèn. Provider usage mới là số
quan sát để settle; không nhận model tự khai usage từ nội dung trả lời.

Reserve quota trước HTTP, settle token thực quan sát. Không có usage giữ NULL và
reservation chờ đối soát; không gán 0 hoặc giá/chi phí giả. Context lớn có thể bị
từ chối sớm bởi cận bảo thủ; operator chọn nguồn/budget phù hợp.

## Kiểm tra chức năng

Từ `backendV1`, chạy harness cô lập với PostgreSQL test và `TEST_REDIS_URL` loopback:

```text
uv run python scripts/run_isolated_tests.py tests/integration/test_compiler_api_645.py tests/integration/test_compiler_queue_645.py tests/unit/test_chat_adapter_645.py tests/migrations -q
```

Ca queue sử dụng Redis/ARQ thật với namespace test riêng rồi dọn. Provider trong
regression là HTTP loopback giả lập. Lượt thử `gh/gpt-6-luna` thật được báo riêng
trong [Context645](../../docs/bao_cao/context645/REVIEW.md), không suy kết quả live
từ các ca mock. Đánh giá chất lượng chuyên sâu để đợt sau theo yêu cầu người dùng.
