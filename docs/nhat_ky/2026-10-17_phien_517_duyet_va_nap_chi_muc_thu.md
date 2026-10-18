# Phiên517 — Duyệt và nạp chỉ mục thử, chưa xuất bản

## Yêu cầu và phạm vi phê duyệt

Người dùng trả lời yêu cầu duyệt cụ thể của phiên516:
**Duyệt, nạp chỉ mục thử; chưa xuất bản**. Phạm vi gồm hai chỗ hiệu đính theo
ảnh và chuyển tiêu đề thành heading, giữ mọi số/mã. Không mở rộng thành quyền
xuất bản, sửa nguồn khác hoặc chạy benchmark sinh đáp án.

Theo skill ingestion, thực hiện riêng review nguồn và build staging. Ghi
actor `user-via-codex-cli` cùng tham chiếu xác nhận chat
`call_11250befa2c945e6acf45253aa7176ca`; không giả danh tài khoản cán bộ DB.

## Thực hiện

- Binding `bnd_58509a6c7f92`, revision2 `ks_rev_be5b393c11af`.
- Trước duyệt: đối chiếu hash đã được trình người dùng,
  `86e6626bffef32c08bd69259a1a0391180e40ac0c0ed8b23e43e78f35a675128`;
  kiểm tra canonical bytes, binding/source/index hiện tại và lưu snapshot trước.
- Gọi `source_ingestion_service.review_source_revision` với quyết định approved,
  ghi chú nguồn xác nhận và giới hạn staging-only. Revision chuyển ready;
  active_source_revision_id chuyển sang bản đã duyệt theo lifecycle hiện có.
  **Đây không phải publication/index switch**.
- Gọi `vector_generation_service.build_generation_for_source` với expected source
  revision và generation hiện hành `vg_a6e3190d11af`. Không parser/OCR/reparse.
- Embedding thật `bge-m3` tại provider `prov_rtx5090_vllm`. Runtime guard chỉ nhận
  provider và endpoint nội bộ đúng DB đã kiểm tra; không fallback cloud.

## Kết quả kiểm chứng thật

- Index mới `idx_rev_06ce7617d508`, trạng thái **ready/staging**.
- **65chunks / 52facts**. DB/Qdrant parity:65expected/65verified, point IDs,
  revision/content hashes khớp. Candidate artifact validation PASS.
- `derived-bundle-v1` hash
  `f4e41f87fe0aae2ceb2607116ffcdccf82fa7b8665d77d3d1548d5a3a234e6ef`.
- Qdrant count đúng65points của index mới có is_retrievable=false.
- Active index vẫn `idx_rev_33508043e816`; collection epoch4/generation không đổi.
  Snapshot fingerprint phục vụ trước/sau trùng nhau;21bindings còn lại nguyên vẹn.
- Gọi loader `load_published_blocks` bằng snapshot phục vụ, giới hạn binding này:
  chứng cứ vẫn thuộc source cũ `ks_rev_fafaaf1e6106`, không lọt revision2 qua
  việc đổi active_source pointer. Không chỉ suy trạng thái từ UI.
- Không gọi activate/promote/publish. Không xóa index/points hoặc nguồn cũ.

## Artifact bền vững

S3StorageDriver, đọc lại từng object và kiểm tra hash:

- `snapshots/markdown-trials/517/bnd_58509a6c7f92/before.json`, SHA256
  `02f490e86c16eaf72ce16b93c14610f87c2dbfd00c065e8361ca39741ac57c4e`:
  snapshot trước/metadata revision cần duyệt và phạm vi xác nhận.
- `snapshots/markdown-trials/517/bnd_58509a6c7f92/result.json`, SHA256
  `456b934ed57d5290a5e5ee0b4f007f86c8907ec14726e16f64a2478af409673f`:
  review actor, index, parity, provider, kiểm tra không phục vụ.
- PDF/ảnh/ledger đối chiếu vẫn giữ ở prefix516, không sửa raw artifacts.

## Lệnh và giới hạn

CWDbackend: `.venv/Scripts/python.exe -` chạy inline orchestration qua service
hiện có, exit0. Preflight/hash/backup/review/build/candidate-validation/Qdrant
count/live-evidence isolation/readback: **PASS**.

Không sửa production code, không cần fullpytest/build cho thao tác vận hành này.
Không chạy retrieval A/B, LLM sinh đáp án hoặc chấm chất lượng; parity không
chứng minh RAG trả lời tốt hơn. Không reset/seed/restart/deploy/commit/push,
không đổi model/prompt/Top K, không xuất bản.

Bước tiếp theo an toàn là kiểm tra candidate so với snapshot cũ, vẫn không
chuyển publication nếu chưa được người dùng cho phép.
