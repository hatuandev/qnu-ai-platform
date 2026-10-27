# Phiên 646 — Phiên bản, duyệt và xuất bản backendV1

Ngày 26/10/2026, Asia/Bangkok.

Người dùng yêu cầu triển khai bước 3 BE sau Compiler645. Vòng đời document/version,
approve/publish/supersede/withdraw do QNU định nghĩa; Kotaemon chỉ tham khảo ở tổ
chức nguồn/citation. Người dùng ưu tiên chức năng, chưa yêu cầu benchmark chất lượng.

## Thay đổi

- Thêm domain `knowledge/publication`: document key tường minh, version tăng dần,
  snapshot model/prompt/source revision và hash output; bản gốc Compiler không sửa.
- Preview actor/action/reason/hash/sequence/active version/expiry; quyết định có
  Idempotency-Key và receipt/audit cùng transaction. Recheck membership/role lúc
  xác nhận. Reviewer/admin approve, admin publish/withdraw; member đọc có scope.
- Thay thế atomic và partial unique index một published/document. Khôi phục bản cũ
  cần quyết định duyệt/xuất bản mới. Cờ approved thiếu receipt không cho publish.
- API đăng ký/list/detail/version/history/draft và published. Read published kiểm
  receipt, nguồn/hash hiện hành; stale/mất/hỏng không trả dữ liệu giả. Withdraw
  vẫn hoạt động khi nguồn hỏng, không xóa bằng chứng hoặc tự publish bản khác.
- Migration0008 tạo 4 bảng mới với FK tổ hợp/ownership; không đổi migration cũ,
  chưa áp DB phục vụ. OpenAPI tái sinh 54 path/72 operation, path cũ giữ nguyên.
- Sửa hẹp LocalBlobStore Windows đã được nêu ở bước 3: khóa stripe cùng đích trong
  process + read PermissionError retry có giới hạn; atomic staging giữ nguyên,
  chỉ thành công khi bytes đích khớp. Permanent denial/khác bytes vẫn thất bại.

## Bằng chứng

- Baseline **2 FAIL** đúng publication API404 và read denial sau denied replace.
- Migration đầu **FAIL** vì generated JSONB thiếu `sa.` cho Text; sửa migration mới.
- Smoke **12 PASS**, 6,13s; focused32PASS,50,85s; focused cuối **35 PASS**,72,20s.
- Full v1 **334 PASS / 0 FAIL / 0 SKIP**,237,43s,exit0;harness244,24s.
- **17 ca mới đều PASS**, không mất ca cũ; writer concurrency lỗi645 nay PASS.
  Có ca deterministic chứng minh xử lý transient read, permanent denial không
  thành success và nhiều adapter cùng ghi giữ đúng bytes.
- Ruff `qnu scripts tests alembic` PASS; format13file PASS; migration/ORM/sentinel,
  auth/revocation, stale preview/source, concurrent publication, tampered/missing
  artifact, version replacement/restore và receipt-negative đều được thực thi.
- **475/475 file Python legacy app** giữ hash; Compiler/ModelOps/OCR runtime v1
  không sửa. **6 DB test,0 còn lại**, receipt và sentinel/version legacy giữ.

## Lệnh

Cwd `backendV1`; wrapper ignored gọi harness DB test loopback tạm, không in secret:

```text
.venv/Scripts/python.exe -X utf8 -B storage/context646/run_checks.py baseline tests/integration/test_publication_646.py tests/unit/test_local_storage_retry_646.py -q --tb=short
.venv/Scripts/python.exe -X utf8 -B storage/context646/run_checks.py focused-final tests/integration/test_publication_646.py tests/unit/test_local_storage_retry_646.py tests/unit/test_local_blob_store.py tests/integration/test_knowledge_regressions_639.py tests/migrations -q --tb=short
.venv/Scripts/python.exe -X utf8 -B storage/context646/run_checks.py full tests -q --tb=short
.venv/Scripts/ruff.exe check qnu scripts tests alembic --output-format concise
```

Không sửa .env/dependency, không live LLM/OCR, không Compiler legacy, không dữ liệu
thật, không publish/reindex/restart/deploy/commit/push. Các lifecycle mutation chỉ
thực hiện trên DB test. Storage lock không phải distributed lock và retry không
bảo đảm mọi filesystem hết sharing violations.

[Báo cáo646](../bao_cao/context646/REVIEW.md) ·
[API](../../backendV1/docs/compiled-publication.md) ·
[Snapshot](../memory/snapshots/2026-10-26_session_646.md).

Bước sau: cấu hình/migrate runtime được phép khi vận hành. Nếu tiếp tục phát triển
BE thì indexing chỉ nhận bản từ API published có kiểm quyền/receipt/hash/nguồn;
không lấy draft/history làm nội dung hiện hành. Chưa xây indexing/RAG/FE đợt này.
