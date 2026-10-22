# Phiên 587 — Trang tri thức, phạm vi năm và đọc nguồn

## Yêu cầu và phạm vi

Người dùng đồng ý triển khai ba ưu tiên học từ llm_wiki: LLM biên soạn trang
nguồn/thực thể/khái niệm; giữ phạm vi năm và căn cứ; chatbot chủ động mở trang,
đọc thêm nguồn có giới hạn. Giữ parser/canonical QNU, ModelOps, Quality Gate và
publication hiện có. Không xử lý lại kho thật, không commit/push/restart/deploy.
Git đầu phiên sạch, HEAD `83415add`; không ghi đè thay đổi của người dùng.

Áp dụng skill clean-code, backend, ingestion, RAG, ModelOps và frontend phù hợp
phạm vi. Không tạo agent phụ hoặc sao chép triển khai GPL của llm_wiki.

## Thay đổi

- Compiler hai giai đoạn, hợp đồng JSON nghiêm ngặt, quote/number/code/year/hash
  validation; carry heading cha nguyên văn và retry lỗi hợp đồng có ngân sách.
- Lưu bundle theo source/chunk/index revision; không cần bảng/migration mới.
- Model/provider qua DB hiện hành, usage giao dịch riêng; lỗi hiện unavailable.
- API read-only có quyền và UI Trang tri thức, Xem nguồn; không gọi LLM khi GET.
- RAG đọc hai lượt mặc định, dùng trang làm điều hướng và canonical làm bằng
  chứng; giữ source/year/condition/exception/publication và giới hạn context.
- Sửa thứ tự gắn wiki policy trước seal readiness sau khi full regression phát
  hiện chứng nhận bị stale; thêm regression chống thay đổi policy âm thầm.

Chi tiết file, phương pháp, lỗi phát hiện và giới hạn:
[Báo cáo triển khai/kiểm chứng](../bao_cao/context587/IMPLEMENTATION_AND_VALIDATION.md).
[Quy trình sử dụng](../quy_trinh/16_trang_tri_thuc_va_doc_nguon.md).

## Kiểm chứng

DB test riêng và LocalStorage riêng; xác minh DB/MinIO/Qdrant local, không
migration DB chung. Full suite không có provider credentials, endpoint ngoài
chặn về loopback cổng 1. Gọi LLM thật chỉ với dữ liệu tổng hợp trong test DB riêng.

- Baseline trước sửa: 2.985 PASS / 18 FAIL / 17 SKIP, exit 1.
- Bộ trọng tâm cuối: 162 PASS, exit 0. Bao gồm compiler, navigation, persistence,
  reader, source context, automatic ingestion và smart approval API.
- Ruff: 21 file Python PASS/exit 0. Biome: 6 file PASS/exit 0; dùng `--line-ending=lf`
  theo AGENTS, không sửa cấu hình formatter CRLF đang có của repo.
- Frontend: 15 test hành vi/render PASS/exit 0; `npm run build` PASS/exit 0, gồm
  TypeScript. Visual preview bị browser chặn; không ghi nhận visual/E2E PASS.
- ModelOps thật: ba trang, hai lượt biên soạn; hai lượt mở trang/đọc nguồn, năm
  block canonical. Không đổi model, không benchmark 64 hoặc công bố tăng điểm.
- Full release: 3.026 PASS / 18 FAIL / 17 SKIP, exit 1 — FAIL; exact 18 IDs/message khớp baseline,
  41 ca mới PASS, không mất test cũ. Ba DB test đã dọn; Storage giữ vì policy.

Lệnh thực (root repo, qua helper chỉ tạo tài nguyên test có owner marker):

```powershell
backend/.venv/Scripts/python.exe -X utf8 .antigravity-bridge/validation/context587gate_checks.py run --label focused-release tests/test_knowledge_wiki.py tests/test_wiki_navigation.py tests/test_wiki_persistence.py tests/test_qnu_serving.py tests/test_source_reader_api.py tests/test_document_reader_structure.py tests/test_source_context_stage2.py tests/test_context570_evidence_scope.py tests/test_automatic_ingestion.py tests/test_smart_approval_api.py
backend/.venv/Scripts/python.exe -X utf8 .antigravity-bridge/validation/context587gate_checks.py run --label full-release
```

Lệnh frontend từ `frontend`: `node --test` hai file `knowledge-wiki.test.mjs` và
`qnu-document-reader.test.mjs`; Biome scoped sáu file; `npm run build`.
Lệnh backend thực, cwd, exit và XML lưu trong artifact có liên kết ở báo cáo.

## Dữ liệu và bàn giao

Seal read-only trước/sau của sáu nhóm dữ liệu vận hành khớp. Không thay nguồn,
model, chỉ mục hoặc publication trong DB dùng chung. Source cũ chưa có wiki;
cần revision mới khi được người dùng yêu cầu thử thật.

DB test và Storage được chốt trạng thái dọn trong báo cáo. Kiểm duyệt tự động
chặn xóa Storage tạm; không tắt bảo vệ hoặc đổi công cụ để vượt chặn.
Không tự hợp nhất entity xuyên nguồn; không coi trang dẫn xuất là fact đã duyệt.
