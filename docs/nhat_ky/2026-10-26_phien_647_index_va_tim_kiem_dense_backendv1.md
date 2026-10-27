# Phiên 647 — Index và tìm kiếm dense backendV1

Ngày 26/10/2026, Asia/Bangkok. Người dùng yêu cầu triển khai bước tiếp theo sau
publication646, cung cấp server AI và credential, sau đó sửa credential thiếu ký tự.
Ưu tiên backend hoạt động; đánh giá chất lượng corpus để sau. Không cài Haystack.

## Phạm vi và thay đổi

- ModelOps thêm dimension embedding gắn endpoint/model; adapter OpenAI-compatible
  lấy provider/key/grant/capacity/quota từ DB, kiểm response strict, không retry ngầm.
- `knowledge/index`: run/input/chunk với FK scope và publication receipt, chia
  đoạn/bảng giữ citation, ô/header/span/row index/footnote. Không sửa OCR gốc.
- ARQ worker ghim snapshot/config, lease/heartbeat/fencing, durable dispatch và
  reconcile. Raw embedding/vector staging/receipt cho resume; in-flight chưa rõ
  kết quả chuyển uncertain, không tự gửi lại model.
- Qdrant collection riêng mỗi generation, deterministic point ID; chỉ nhận tên
  thuộc v1, xác nhận upsert completed. Kích hoạt sau khi kiểm snapshot và manifest,
  lỗi replacement giữ active index cũ.
- Search kiểm quyền/nguồn trước và sau query embedding, scope trước TopK và kiểm
  hit với SQL/manifest. Trả text/structure/citation; lỗi provider/hạ tầng không
  thành “không có dữ liệu”. Withdraw/source stale loại nội dung; receipt/version
  mới cần generation mới. Chưa sinh câu trả lời bằng LLM.
- Migration0009/3bảng + unique publication scope; không sửa migration cũ. OpenAPI
  58path/77operation, thêm4path/5operation và giữ54path cũ. ModelOps schema thêm
  dimension/status; không thêm dependency hoặc LLM key trong `.env`.

## Kiểm chứng thực chạy

| Kiểm tra | Kết quả |
|---|---|
| Baseline tính năng | 1FAIL: dimension chưa được API chấp nhận422 |
| Smoke đầu | Collection ERROR do syntax mới, đã sửa trước smoke2PASS |
| Focused trước hardening | 7PASS rồi38PASS |
| Negative hardening baseline | 2FAIL/2PASS: structure chưa seal, upsert chưa xác nhận |
| Focused cuối | 43PASS/0FAIL/0SKIP,101,29s |
| Full v1 | **376PASS/0FAIL/0SKIP**,341,56s,exit0;harness348,34s |
| Ca mới/ca mất | 42/0; invariant fail-loud giữ cùng ID, chuyển sang reranker còn stub |
| Ruff/format/migrationORM | PASS; format22file; head0009 |
| Hash và encoding | 475legacy app giữ;16file Python đổi/19file mới trong v1; UTF-8 không BOM/LF |
| Dọn tài nguyên | 12DB theo receipt,0còn;0collection vector v1; live queue keys dọn |

401 xảy ra với credential đầu cả qua adapter và gọi trực tiếp. Sau khi người dùng
sửa credential, live BGE-M3 trả4vector1024chiều/51token trong0,875s; tokenizer
báo max_model_len8192. Không lưu key/fingerprint vào source/docs/log.

Live luồng API → ModelOps → Redis/ARQ → BGE-M3 → Qdrant → search PASS,1job/0lỗi,
2chunk; index1,906s/search0,625s. Bảng mẫu150 đứng đầu, citation đúng revision.
Sau withdraw không còn nội dung và không phát sinh embedding usage. PDF tổng hợp,
OCR/chat fixture giả lập; không gửi corpus nội bộ. Đây là functional check nhỏ,
không chứng minh chất lượng trên tài liệu QNU hoặc hiệu năng tải.

## Lệnh và bằng chứng

Cwd `D:/DuAnPhanMem/qnu-ai-platform/backendV1`; wrapper ignored đọc cấu hình hạ
tầng vào process, harness tạo/migrate/dọn DB test loopback và giữ sentinel legacy.

```text
.venv/Scripts/python.exe -X utf8 -B storage/context647/run_checks.py hardening-baseline tests/integration/test_index_api_647.py::test_table_structure_tampering_is_rejected tests/unit/test_qdrant_adapter_647.py -q --tb=short
.venv/Scripts/python.exe -X utf8 -B storage/context647/run_checks.py focused-final tests/integration/test_index_api_647.py tests/unit/test_embedding_adapter_647.py tests/unit/test_index_chunking_647.py tests/unit/test_qdrant_adapter_647.py tests/migrations -q --tb=short
.venv/Scripts/python.exe -X utf8 -B storage/context647/run_checks.py full tests -q --tb=short
.venv/Scripts/python.exe -X utf8 -B storage/context647/probe_index.py
.venv/Scripts/ruff.exe check qnu scripts tests alembic --output-format concise
```

Log/XML/receipt và live/scope/OpenAPI/test/cleanup JSON nằm trong ignored
`backendV1/storage/context647/`. Không đưa dữ liệu nguồn hoặc credential vào Git.

## Giới hạn và bước sau

Chưa migrate0009/cấu hình provider trên DB phục vụ, restart/deploy API/worker,
publish/index tài liệu thật hoặc commit/push. Các trạng thái thử chỉ trong DB riêng.
Chưa hybrid/BM25/sparse/rerank, answer/chat, FE, GC generation hay quality benchmark.
Chưa thử qwen3.5-9b/bge-reranker-v2-m3/live Nemotron trong batch này.

Bước sau: nối các đoạn/citation từ search vào runtime trả lời qua ModelOps;
vẫn kiểm scope, evidence, không suy đáp án khi thiếu căn cứ hoặc provider lỗi.

[Báo cáo647](../bao_cao/context647/REVIEW.md) ·
[API](../../backendV1/docs/dense-indexing.md) ·
[Snapshot](../memory/snapshots/2026-10-26_session_647.md).
