# Context600 — Audit và baseline Wiki 4–6

Ngày 22/10/2026. Phạm vi: mã và kiểm thử Wiki 4–6; không thay nguồn vận hành,
ModelOps, Quality Gate, publication, vector hoặc active pointer.

## Bằng chứng trước sửa

- `git status --short` và `git diff --stat`: sạch, exit0.
- Đã đọc AGENTS, PROJECT_CONTEXT (các mốc gần nhất), verification,
  workflow/memory, security/Git và skill clean-code/backend/RAG/evaluation/frontend.
- Python theo pyproject: >=3.12,<3.13; venv có sẵn. Không cài gói mới.
- Preflight thật: development; PostgreSQL/MinIO/Qdrant loopback; không job queued/
  running trong collection benchmark. Actor xác thực có quyền quản trị.
- Nguồn hiện tại có 12 revision; source `ks_rev_993a7ad91b32`, index staging
  `idx_rev_6bf0d6f86b1b`, generation `vg_a6e3190d11af`. Không active index.
- SHA PDF `082c412e145a9ef39ae50110ae16cc80c17d612e2f0e00f9d16ee78c7c1c3b02`;
  648851 bytes, Storage readback khớp. Qdrant 2943 points, 0 retrievable.
- Freeze kiểm đủ64 ID duy nhất, cùng questions/criteria/rubric/gold spans,
  33 fact mappings không đổi, cùng canonical/revision/index/vector/profile.
  Luna chính/Qwen dự phòng giữ nguyên; benchmark dùng Luna-only scope hiện có
  để so sánh, không sửa cấu hình DB. Timeout provider30s, timeout service150s.

Artifact riêng được ignore: `backend/storage/context600/baseline/`. Runner mới
có run-intent và khóa OS; từng request chỉ gửi một lần, history theo session giữ
quy tắc cũ. Usage audit được giữ. Không chạy synthetic model đồng thời.
Baseline64 hoàn tất trước sửa app:58/60 tri thức,48/50 positive,10/10 negative,
4/4 social; FAIL P10/P15;135/135 citations,0runtime,167 Luna/0fallback. Runner,
scorer và postcheck exit0. Kết quả599/597 vẫn là lịch sử, không ghép điểm.

## Bản đồ kiến trúc thực tế

Nguồn → `KnowledgeSourceRevision` và cặp canonical MD/Structured JSON →
`source_artifact`/unit manifest/context graph → `KnowledgeChunkSet` chứa wiki
bundle có hash → `KnowledgeIndexRevision.parity_report` ghim cùng bundle →
snapshot binding/index/vector → `rag/wiki_context` chọn trang trong budget →
canonical `EvidenceBlock` → claim binding/audit/citation.

| Thành phần | Hiện có và tái sử dụng | Khoảng hở cần mở rộng |
|---|---|---|
| wiki_schemas/compiler/extractive | 3 loại trang, quote/unit, vai trò năm, exact extractive, version/hash | Liên kết giữa các trang/nguồn; metadata điều hướng |
| wiki_build | ModelOps động, budget, lỗi unavailable có mã | Tái dùng kết quả tương thích qua revision |
| chunk_set_service/derived_bundle | Khóa source, unique revision/config, hash/review/index seals; không đổi active pointer | Hiện chủ động không reuse wiki qua revision |
| generation_candidate/retriever | Candidate có quyền, published snapshot và stale check | Dựng bản đồ từ đúng snapshot này |
| wiki_context | Chỉ canonical, lọc năm theo role, giới hạn calls/chars, cache request | Duyệt liên kết có giới hạn và chặn cache sau thu hồi |
| wiki_views/router/UI | GET read-only theo revision, exact source sheet, auth, trạng thái lỗi | Liên quan/backlinks, phiên bản và Advanced Review |
| source_links/semantic review | Structural closure theo bảng/field, annotation và approval hiện có | Không dùng context graph trong một nguồn như graph identity xuyên nguồn |

Không thêm framework, worker hoặc graph database. Không dùng code GPL.

## Cô lập regression

DB mới do phiên tạo có tên `qnu_test_context600_<nonce>`, comment chứng minh sở
hữu; tạo schema chỉ trên DB này. Storage local riêng dưới runtime600. Endpoint
dịch vụ thật bị thay bằng loopback không phục vụ trong môi trường pytest;
không sao chép credentials. Việc tạo DB test không phải migration DB ứng dụng.
Chi tiết thực chạy, đối chiếu exact IDs và cleanup ở [VALIDATION_REPORT](VALIDATION_REPORT.md).

Đã tạo DB49 bảng với comment/nonce sở hữu; chưa sao chép credential. Harness
pytest bổ sung audit hook chặn kết nối dịch vụ/model thật, chỉ cho DB test và
listener do process test tự mở; xóa TEST_DATABASE_URL kế thừa trong process con.

Hai tái hiện hành vi trước sửa (PostgreSQL thật, compiler fixture, không LLM):

- `test_revoked_publication_pointer_rejects_old_wiki`: **FAIL** đúng assertion;
  gỡ active pointer nhưng loader trả3 trang từ snapshot cũ.
- `test_unchanged_revision_reuses_wiki_without_inference`: **FAIL** đúng assertion;
  nguồn/cấu hình không đổi qua revision nhưng model generator bị gọi2 lần.

Receipt `checks/baseline-boundary-actual-run.json` và `baseline-reuse-run.json`,
cwd backend, exit1. Lượt đầu `baseline-boundary` dùng đường dẫn tương đối sai với
cwd nên pytest exit4, không chạy test; giữ receipt, không coi là lỗi hành vi.
