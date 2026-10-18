# Phiên518 — Xuất bản bản sạch đã duyệt

## Phạm vi

Người dùng yêu cầu xuất bản ngay sau khi duyệt và dựng staging ở517. Chỉ áp
dụng nguồn bảng52ngành2025 trong app local; không deploy lên Dokploy/Git.
Theo skill ingestion, đối chiếu source/hash/review/bundle/Qdrant trước đổi
pointer, dùng service publication có CAS và giữ points cũ.

## Thực hiện và bằng chứng

- Binding `bnd_58509a6c7f92`; source đã duyệt `ks_rev_be5b393c11af`.
- Canonical hash kiểm lại:
  `86e6626bffef32c08bd69259a1a0391180e40ac0c0ed8b23e43e78f35a675128`.
- Trạng thái nguồn ready/review approved; index thử ready,65chunks/52facts.
  Kiểm candidate artifacts, DB chunks/facts và bundle PASS; Qdrant parity
  chạy lại theo pointIDs/hash:65/65PASS, không chỉ dùng kết quả cũ.
- Gọi `IndexBuildService.promote_index_revision` với expected binding epoch1,
  actor `user-via-codex-cli`, lý do yêu cầu xuất bản rõ ràng. Service dùng
  `swap_sealed_revision` trong cùng generation, tái kiểm nguồn sau remote I/O.
- Chuyển index `idx_rev_33508043e816` → `idx_rev_06ce7617d508`.
- Audit `act_26b64438daf7`, action promote, binding epoch2.
- Collection epoch4→5, generation `vg_a6e3190d11af` giữ nguyên.

## Kiểm tra sau commit

-65points index mới is_retrievable=true;65points index cũ vẫn còn nguyên,
  không deactivate/delete để giữ khả năng phục vụ snapshot cũ/quay lui.
- Snapshot hiện hành chọn index mới, không chứa index cũ. Fingerprint cache
  đổi theo epoch và revision, không phải xóa toàn bộ cache chung.
- Loader chứng cứ `load_published_blocks` với snapshot thật đọc đúng source
  revision2, không còn revision cũ trong phạm vi binding này.
-52facts của index được snapshot chọn đều trỏ source revision2.
-21bindings khác: active source/index/epoch/status giữ nguyên. Không sửa
  prompt, model, Top K hoặc tệp nguồn, không tạo nguồn mới.
- Không chạy rollback thực tế; giữ đích cũ và snapshot trước trong artifact.

## Snapshot và kết quả

S3StorageDriver readback/hash PASS:

- `snapshots/markdown-trials/518/bnd_58509a6c7f92/before.json`, SHA256
  `df76a0e13054b81b002eedd9020bc875842ebb31c0bca55c0963830ef2644e58`.
- `snapshots/markdown-trials/518/bnd_58509a6c7f92/result.json`, SHA256
  `c82a4e50809f71163c5631273ad5dbb78692cf71e864c723d2787c1b8883e933`.

Before ghi pointers22bindings, hash nguồn, epoch và đích quay lui; kỳ vọng
epoch để rollback sau lần promote này là2, cần kiểm tra lại trạng thái thật
nếu có thao tác khác. Không tự dùng snapshot để ghi đè thay đổi mới.

## Kiểm chứng và giới hạn

CWDbackend: `.venv/Scripts/python.exe -` inline vận hành qua service hiện có,
exit0. Preflight/parity/promote/audit/readback/live-evidence isolation: **PASS**.

Không sửa production code, không chạy fullpytest/build cho thao tác vận hành.
Không gọi embedding/reranker/LLM hoặc chạy/chấm benchmark. Việc xuất bản và
đối soát thành công không chứng minh chatbot trả lời tốt hơn; A/B chất lượng
vẫn NOT RUN. Không reset/seed/restart/deploy/commit/push. Đã tuân quyền mới
của người dùng, thay thế giới hạn chưa xuất bản ở517 chỉ cho đúng nguồn này.
