# Phiên 484 — Quản lý thuật ngữ tìm kiếm theo Kho tri thức (glossary)

Ngày: 2026-10-15. Phạm vi: backend `knowledge`/`rag`, frontend `knowledge`, manifest quyền, kiểm thử.

## 1. Thiết kế đã chốt (5 điều kiện người dùng)
- Bảng mới `knowledge_glossary_terms` + `knowledge_glossary_audits` + `knowledge_glossary_settings`;
  quan hệ có hướng A→B, single-hop, không đệ quy; entry luôn `pending` khi tạo.
- Chuẩn hóa NFC/whitespace/casefold phát hiện trùng, không bỏ dấu; cụm→đích khác = xung đột → skip.
- RBAC: tạo/sửa cần `ai.knowledge.update`; duyệt/từ chối/thu hồi/toggle cần `ai.knowledge.review` (mới,
  đã khai báo `qnu-ai-permissions.json`, manifest 27→28); OCC `expected_version` → 409; lỗi RFC 7807.
- Expansion: `SearchQuery` role `glossary`, `ORIGINAL_SHARE=0.65`, `GLOSSARY_LEXICAL_WEIGHT=0.3`,
  `MAX_GLOSSARY_MATCHES=2`, `MAX_TARGET_TOKENS=12`; câu gốc giữ nguyên cho dense/rerank;
  bỏ qua target số/năm/mã, scope mờ/xung đột có `reason`.
- Cache: `policy_version + :glossary-v{version}/:glossary-off`; toggle/bump version + invalidate;
  trace `alias_id/version/phrase/term/weight/skipped`; `db=None` → disabled trace, không crash.

## 2. File đã thêm/sửa
- Thêm: `knowledge/glossary_schemas.py`, `knowledge/services/glossary_service.py`,
  `alembic/versions/20261015_glossary_terms.py` (head `20261012_sync_struct_review`, CHƯA apply),
  `rag/glossary_expansion.py`, `tests/test_glossary_terms.py`,
  `frontend/.../tabs/collection-glossary-tab.tsx`.
- Sửa: `knowledge/models.py`, `knowledge/router.py` (7 endpoints), `rag/query_expansion.py`,
  `rag/evidence_search.py`, `rag/evidence_pipeline.py`, `rag/retriever.py`, `rag/service.py`,
  `qnu-ai-permissions.json`, `tests/test_permission_contract.py` (27→28),
  FE `types/knowledge.ts`, `services/knowledge-api.ts`, `collection-detail-page.tsx`,
  `routes/knowledge.$collectionId.tsx`.
- FE: tab `Thuật ngữ` + deep link `?tab=glossary` + disclaimer
  "Thuật ngữ hỗ trợ tìm kiếm, không thay thế căn cứ trong tài liệu."

## 3. Sự cố trong phiên và cách xử lý
- `test_glossary_terms` đỏ ban đầu vì thiếu module service → triển khai đủ lớp rồi xanh.
- Full suite vỡ 42 + 11 mới (mock `AsyncMock`/`db=None`/manifest thiếu quyền):
  thêm `_fetch_one/_fetch_all/_fetch_get` chịu sync/async test doubles,
  `resolve_glossary_queries` early-return disabled trace khi `db is None`,
  khai báo `ai.knowledge.review` trong manifest. Không sửa test nghiệp vụ để làm xanh.

## 4. Kết quả kiểm thử cuối (2026-10-15)
- `tests/test_glossary_terms.py`: 31 passed, 1 skipped (gate persistence `TEST_DATABASE_URL` sqlite).
- Cụm trọng tâm (glossary + permission + evidence + rag rows/gen/temporal/contract): 130 passed, 1 skipped.
- Full backend: 12 failed, 1634 passed, 17 skipped — 12 failed TRÙNG KHỚP tập baseline
  (`backup_launcher` ×1, `consulting_dispatcher` ×2, `publishing_v2_*` ×6,
  `rag_data_truth` ×1, `trust_boundary` ×1, `universal_tools` ×1); 0 regression từ glossary.
- `ruff check` scoped sạch; FE `tsc --noEmit` + `vite build` đạt (13.79s);
  `biome check` chỉ còn format drift CÓ SẴN trong `knowledge-api.ts` ngoài 103 dòng mới.

## 5. Ràng buộc đã giữ
- Không reset DB, không apply migration, không reparse/reindex/publish, không đổi ModelOps,
  không restart/deploy/commit/push; giữ nguyên thay đổi chưa commit và `docs/tai_lieu`.
- Không chạy bộ 20/82 câu, không gọi model thật; không tự khai thác thuật ngữ mới.

## 6. Ghi chú cho phiên sau
- `docs/memory/PROJECT_CONTEXT.md` đoạn cuối có mojibake có sẵn nên KHÔNG sửa file này trong phiên;
  nội dung cập nhật ngữ cảnh nằm tại log này.
- Muốn bật glossary cho collection: `PUT .../glossary-settings {"is_enabled": true}` (quyền review),
  rồi tạo entry (quyền update) → duyệt (quyền review); migration vẫn cần DBA apply riêng.
