# Context649 — Trợ lý và hội thoại backendV1

Ngày 2026-10-26. Người dùng yêu cầu triển khai bước6 sau API hỏi đáp648, rồi giải
thích bộ skill NVIDIA RAG Blueprint. Phạm vi BE và dữ liệu mẫu riêng; không thêm
framework, install skill, model default hoặc cấu hình phục vụ.

## Kiểm chứng thực chạy

| Kiểm tra | Kết quả |
|---|---|
| Baseline API trước triển khai | 1FAIL do POST assistants404 |
| Smoke + migrationORM | 2PASS/0FAIL/0SKIP,8,59s |
| Focused đầu | 10PASS/0FAIL/0SKIP,65,33s |
| Focused cuối | **38PASS/0FAIL/0SKIP**,230,64s, gồm hội thoại mới +20ca answers648 +migration |
| Full v1 | **413PASS/0FAIL/0SKIP**,592,92s,exit0/harness599,05s;17ca mới/0ca mất |
| Ruff/format | PASS toàn `qnu scripts tests alembic`;20file kiểm format |
| Schema | Migration0010/3bảng chat_* khớp ORM, legacy sentinel/version giữ |
| OpenAPI | **65path/89operation**, thêm6path/11operation,59path cũ giữ |
| Phạm vi source | 749Python baseline,475legacy app giữ;8file v1 đổi/14file mới |
| Live multi-turn | PASS chức năng,2turn completed/answered, history2/replay cùng usage/source đúngrevision |
| Dọn thử | 8DB theo receipt đã dọn/0còn,0collection vector v1 quan sát |

Live với BGE-M3/Qwen3.5-9B/Qdrant/ModelOps thật, PDF tổng hợp/OCR/Compiler mock:

- Lượt đầu HTTP502 `answer_response_invalid`, không coi là thành công. Không có
  raw diagnostic của lượt này nên chưa xác định trường schema nào sai.
- Lượt sau: turn1 completed/insufficient_evidence, turn2 answered; rewriter còn
  nhắc “câu hỏi trước”, chưa độc lập hoàn toàn. Báo cáo giữ nguyên, không gọi lại
  một inference chưa rõ kết quả hoặc xóa evidence failed.
- Bổ sung prompt hướng dẫn thay chủ thể đầy đủ bằng ví dụ tổng quát; đổi hai câu
  hỏi live sang đọc ghi chú và header, không đổi corpus. Lượt cuối2turn answered,
 1,453s và2,266s. Rewrite320token, answer2001/2052token; tổng chat4373token.
  “Bảng đó…” được làm rõ thành “Bảng chỉ tiêu tuyển sinh…”. History GET2turn và
  replay cùng answer usageID PASS. Đây là functional check rất hẹp, không quality benchmark.
- Output cuối đọc đúng header2023/2024 nhưng còn thêm diễn giải ghi chú gắn với
  cột2023 trong khi nguồn chỉ ghi chú chung. **Chưa đạt bảo đảm ngữ nghĩa**; không
  che bằng citation hợp lệ hay điểm PASS của API. Giữ phần này cho evaluation sau.

Credential nhập getpass và thêm qua ModelOps DB thử mã hóa; không đưa secret,
fingerprint key, private prompt/corpus hoặc Base64 OCR vào code/docs/log. Diagnostic
raw chat ignored chỉ chứa dữ liệu tổng hợp đã được phép, không là API raw mới.

## Thiết kế cuối cùng

- `assistants`: config một collection, persona/style, provider/default ModelOps,
  topK/history/output budget, active/revision. Admin quản lý; expected_revision
  chặn lost update. Collection immutable, không ép model cũ/fallback hoặc copy key.
- `conversations`: owner từ actor, assistant revision/snapshot và document scope
  cố định. Owner + membership phải cùng hợp lệ, kể cả platform admin không bypass
  ownership để đọc/gửi chat của người khác.
- Mỗi turn là cặp question/result, lưu original/resolved/history IDs, answer có
  citations/trace hoặc trạng thái lỗi. Sequence/idempotency và unique running
  được bảo vệ SQL; lưu request trước HTTP. Body không nhận owner/history/providerURL.
- Follow-up lấy cửa sổ câu hỏi người dùng completed, không dùng assistant text
  làm facts. Rewriter qua ModelOps có capacity/quota/usage riêng; malformed/clarify
  báo lỗi thật, không giả query. Scope collection/document từ DB không do model đổi.
- Tái sử dụng answer648, thêm internal resolved query/persona và async checkpoint.
  Prompt version2 nói rõ style không thay quy tắc bằng chứng. Không xây RAG pipeline
  thứ hai; index/search/ranking/source/OCR/Compiler giữ nguyên.
- Checkpoint trước/sau HTTP giữ owner/quyền/active/revision/lease; answer tiếp tục
  kiểm nguồn/publication/index/model/citation. Config/permission/archive đổi
  khi đang chạy thì không lưu completed. Expired lease → uncertain khi đọc/gửi
  tiếp; không có tự retry model hoặc worker/cron mới. Late completion bị fence.
- GET history kiểm cited sources hiện hành, ẩn result cũ thành unavailable khi
  source/index không còn hợp lệ; storage/provider lỗi vẫn trả lỗi. Raw DB evidence
  giữ nguyên. Replay completed cũng kiểm nguồn trước trả lại, không gọi model mới.
- Ba bảng `chat_assistants/chat_conversations/chat_turns`, FK scope/unique sequence/
  key/running, migration frozen0010, downgrade từ chối. Không dùng tên bảng legacy.
  Thêm router/wiring/Settings/ownership/test cleanup; không dependency mới.

Ca trọng tâm qua API/PostgreSQL/Qdrant thật + model HTTP mock: create/read owner,
platform owner-bypass404, admin role và collection/document scope, idempotent
replay/key conflict/sequence conflict, persisted failure/no-resend, follow-up trace,
clarify/bad rewrite, source withdrawal history masking, assistant revision,
concurrent busy, expired uncertain, assistant/archive/membership đổi giữa inference,
history budget. 20ca answer648 chạy lại để giữ hành vi cũ.

## Lệnh và artifacts

Cwd `D:/DuAnPhanMem/qnu-ai-platform/backendV1`, đúng venv/lock Python3.12.
Wrapper ignored đọc bí mật hạ tầng vào process không in; harness chỉ tạo/migrate/
dọn DB loopback tạm `qnu_v1_test_*`, giữ sentinel/version legacy.

```text
.venv/Scripts/python.exe -X utf8 -B storage/context649/run_checks.py baseline tests/integration/test_conversations_649.py -q --tb=short
.venv/Scripts/python.exe -X utf8 -B storage/context649/run_checks.py smoke tests/integration/test_conversations_649.py tests/migrations -q --tb=short
.venv/Scripts/python.exe -X utf8 -B storage/context649/run_checks.py focused-final tests/integration/test_conversations_649.py tests/integration/test_answers_api_648.py tests/migrations -q --tb=short
.venv/Scripts/python.exe -X utf8 -B storage/context649/run_checks.py full tests -q --tb=short
.venv/Scripts/python.exe -X utf8 -B storage/context649/probe_conversation.py
.venv/Scripts/ruff.exe check qnu scripts tests alembic --output-format concise
```

Artifacts ignored `storage/context649/`: baseline/OpenAPI seals, log/XML/receipt,
live first-failed/second-abstained/final report, synthetic model replies and turn
JSON, scope/test/cleanup/document checks. Generated migration đã xác minh UTF-8
không BOM và đổi CRLF→LF; không sửa bytecode/source cũ ngoài phạm vi.

## Bộ skill NVIDIA nên dùng thế nào với QNU

[README của NVIDIA](https://github.com/NVIDIA-AI-Blueprints/rag/blob/main/skills/README.md)
chia `rag-blueprint` vận hành, `rag-eval` chất lượng và `rag-perf` hiệu năng. Đây là
hướng dẫn cho coding assistant, không phải plugin cấp trí nhớ cho chatbot. Skill
định tuyến vào playbook, playbook dẫn tài liệu chuyên biệt thay vì nhân bản cấu hình.

QNU đã có qnu-chatbot-builder, qnu-rag-pipeline, qnu-rag-evaluation và ModelOps;
không cần chồng thêm bộ điều phối song song chỉ để theo repo mẫu. Khi muốn cải
thiện skill QNU, nên bổ sung các reference cụ thể vào skill hiện có: hội thoại/
rewrite/nguồn; môi trường và startup; chẩn đoán theo trace; quality và performance
riêng. Lệnh/path/env/restart trong skill NVIDIA chỉ dùng cho NVIDIA Blueprint,
không tự áp vào QNU. Credential QNU tiếp tục qua ModelOps, không lấy hướng dẫn env
key của repo khác để bypass. Phiên này chỉ tham khảo, chưa cài/sửa skill nào.

## Giới hạn

- Chưa migrate0010 vào DB phục vụ, config model/assistant thật, deploy/start/
  restart API/worker, index/publish corpus thật hoặc commit/push.
- Một assistant/một collection; chưa share/public/widget/FE/SSE/tools hoặc memory
  dài hạn. Follow-up chỉ dùng câu hỏi trước, chưa tái diễn giải nguyên đáp án cũ.
- Không semantic verifier hoặc gold multi-turn benchmark; rewrite có thể làm sai
  ý/năm/metric dù JSON hợp lệ. Không tuyên bố citation hợp lệ là answer đúng.
- Lazy expiry, không background resumption. Mất process có thể để usage unknown;
  operator xem ledger/evidence trước chủ động thử lượt mới, không sửa key để retry mù.
- Chưa retention/GC hội thoại hoặc archive xóa dữ liệu. History revalidation phụ
  thuộc source/storage/ModelOps hiện hành, có thể tốn I/O; chưa benchmark tải.

[API/vận hành](../../../backendV1/docs/assistants-conversations.md) ·
[Quy trình26](../../quy_trinh/26_tro_ly_va_hoi_thoai_backendv1.md).
