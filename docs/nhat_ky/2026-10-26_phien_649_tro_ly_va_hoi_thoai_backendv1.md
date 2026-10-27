# Phiên 649 — Trợ lý và hội thoại backendV1

Ngày 26/10/2026, Asia/Bangkok. User yêu cầu bước6 sau answers648 và giải thích
bộ skill NVIDIA. Mục tiêu BE hoạt động, không cài nguyên Blueprint hoặc thêm swarm.

## Thay đổi

- Assistant config một collection, provider/default ModelOps, persona style,
  topK/history/output budget, active/revision; admin quản lý, expected_revision.
- Conversation owner lấy actor server, snapshot assistant/revision/document scope
  cố định; mọi access qua resolver, platform admin không bypass đọc chat người khác.
- Turn lưu cặp question/result/citation/trace hoặc lỗi, original/resolved/history
  IDs, key/hash/sequence/lease. Lưu request trước HTTP, một running, replay không
  model lại; key khác body/sequence cũ báo409.
- Follow-up lấy cửa sổ câu hỏi user completed, không dùng assistant text làm facts.
  Rewriter ModelOps có quota/usage riêng, malformed/clarification lỗi thật.
- Answer648 thêm internal resolved query/persona/checkpoint, promptv2; giữ nguyên
  search/index/ranking/OCR/Compiler. Kiểm assistant/owner/active/lease sau HTTP;
  nguồn/publication/index/model/citation vẫn qua validation cũ.
- History revalidation không gọi model/vectorsearch; nguồn cũ không hợp lệ ẩn
  result/source, giữ row. Expired running lazy→uncertain, không auto retry/resume.
- Migration0010/3bảng chat_* có FKscope/unique key/sequence/running; không tên bảng
  legacy, downgrade giữ evidence. OpenAPI65path/89operation,+6path/+11operation,
 59path cũ giữ. Không dependency mới hoặc LLM key trong .env.

## Bằng chứng

- Baseline1FAIL assistants404 → smoke/ORM2PASS,8,59s → focused10PASS,65,33s →
  focused38PASS/0FAIL/0SKIP,230,64s (17ca mới,20answers648,migration1).
- Full v1 **413PASS/0FAIL/0SKIP**,592,92s,exit0/harness599,05s;17ca mới/0ca mất.
- 8DB theo receipt đã dọn/0còn,0collection vector v1 quan sát; sentinel/version legacy giữ.
- Ruff toàn qnu/scripts/tests/alembic PASS; format20file PASS.
- 749Python baseline,475legacy app giữ;8file v1 đổi/14file mới. Source/docs mới
  UTF-8 không BOM/LF; generated migration CRLF được kiểm byte rồi đổi LF.
- Live đầu schema502; lần sau turn1abstain/turn2answered, rewrite chưa độc lập.
  Báo cáo lỗi giữ. Thêm hướng dẫn rewriter bằng ví dụ chung, thử hai câu đọc
  ghi chú/header khác trên cùng corpus, không nới schema hoặc sửa nguồn.
- Live cuối BGE-M3/Qwen/Qdrant/ModelOps PASS chức năng:2turn answered,
  1,453s/2,266s; chat2001+320rewrite+2052=4373token,history2/replay cùng usage,
  citation đúng revision. OCR/Compiler PDF tổng hợp mock, không corpus nội bộ.
- Model cuối còn gán ghi chú chung cho một cột năm mà nguồn chưa chứng minh;
  **chưa quality/semantic acceptance**, không lấy citation đúng để che ý sai.

## Lệnh

Cwd `D:/DuAnPhanMem/qnu-ai-platform/backendV1`; harness loopback DB tạm riêng,
sentinel/version legacy giữ, không in credential hạ tầng.

```text
.venv/Scripts/python.exe -X utf8 -B storage/context649/run_checks.py baseline tests/integration/test_conversations_649.py -q --tb=short
.venv/Scripts/python.exe -X utf8 -B storage/context649/run_checks.py smoke tests/integration/test_conversations_649.py tests/migrations -q --tb=short
.venv/Scripts/python.exe -X utf8 -B storage/context649/run_checks.py focused-final tests/integration/test_conversations_649.py tests/integration/test_answers_api_648.py tests/migrations -q --tb=short
.venv/Scripts/python.exe -X utf8 -B storage/context649/run_checks.py full tests -q --tb=short
.venv/Scripts/python.exe -X utf8 -B storage/context649/probe_conversation.py
.venv/Scripts/ruff.exe check qnu scripts tests alembic --output-format concise
```

Artifacts ignored storage/context649: seals/OpenAPI, test log/XML/receipt,
live failed/abstained/final + synthetic model replies/turn JSON, scope/test/cleanup
và document checks. Credential qua getpass/ModelOps mã hóa DB thử, không vào code/docs/log.

## Giới hạn và skill NVIDIA

Chưa migrate/config/deploy/start/restart phục vụ, corpus thật/pub/index/Git.
Chưa chia sẻ/public/widget/FE/SSE/tools, semantic verifier/gold multi-turn hoặc
retention/GC/background resume. Follow-up chỉ dùng user questions và có thể viết
lại sai ý dù schema đúng. Trước dùng thật cần migrate0010/config/quality phù hợp.

Skill NVIDIA là playbook coding-agent vận hành/quality/perf, không là trí nhớ
chatbot. QNU đã có skill chuyên ngành: nên học tổ chức reference và tách báo cáo
chất lượng/hiệu năng, không cài chồng điều phối hay dùng path/env/restart của NVIDIA
cho QNU. Chưa cài/sửa skill phiên này; giải thích chi tiết trong báo cáo.

[Báo cáo649](../bao_cao/context649/REVIEW.md) ·
[API](../../backendV1/docs/assistants-conversations.md) ·
[Snapshot](../memory/snapshots/2026-10-26_session_649.md).
