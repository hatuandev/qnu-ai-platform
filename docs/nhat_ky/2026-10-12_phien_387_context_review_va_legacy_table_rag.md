# Phiên #387 — Hiệu đính ngữ cảnh, migration và RAG nguồn cũ

Ngày 12/10/2026. Tiếp tục Kế hoạch14 sau khi Docker/PostgreSQL hoạt động; phiên có hai lần người dùng ngắt để hỏi về reset DB. Giữ nguyên kho thật để kiểm đối chiếu, không reset/upload/reparse/publish thay người dùng.

## Kết quả thực hiện

### Ngữ cảnh và duyệt revision

Thêm SourceContextEditRequest/FactContextEdit có kiểu, hash kỳ vọng, reason tối thiểu, schema không nhận field ngoài phạm vi. Sửa ngày/năm ban hành, năm chủ đề hoặc năm/phương thức/đơn vị của fact tạo bản nguồn mới từ canonical Markdown, không gọi OCR. Metadata snapshot và raw cells/header gốc không bị ghi đè mất dấu. Audit gồm actor/reason/time, original fact ID và quyết định người duyệt. Row lock và latest revision/hash guard chặn sửa từ bản cũ.

Revision mới bắt buộc review_required; giữ active source/index đến khi duyệt. Khi duyệt, cập nhật active source nhưng không đổi active index; cần staging/publish chủ đích. Fact context được duyệt mới có status verified và fact_set_hash mới. Remap fact ID qua full cell evidence khi canonical page normalization đổi content hash; không remap theo value đơn lẻ.

UI Ngữ cảnh dùng Sheet/primitives, TanStack Form/Query và Zod; không tạo primitive riêng. Có tìm fact, giới hạn 50 kết quả chọn, hiển thị giá trị/trang/header, chỉ sửa ngữ cảnh chứ không sửa raw value. Không sửa field nào thì nâng artifact ở draft. Chưa có bulk backfill tự động hoặc editor kỳ/khoảng thời gian tổng quát.

### Schema và query

Áp dụng migration additive `20261012_fact_temporal_context` từ head20261011_independent_index đã kiểm trước: entity_code, attribute_code, applicability_year, temporal_type, admission_method, unit nullable và ix_fact_snapshot_context. Không backfill năm từ filename/upload/date văn bản. Materialize facts mới chiếu typed fields từ JSONB context, lookup tôn trọng snapshot và hỗ trợ legacy null.

### Bảng xuyên trang và nguồn legacy

Kiểm thực tế thấy dòng CNTT36 nằm trang12 nhưng header2024/2025 ở trang11. Legacy MD có separator sau dòng32 và trang sau mở bằng body33, không phải header mới. Thuật toán mới chỉ nối khi trang kế tiếp, cuối trang trước là bảng, đầu trang sau là body, cùng width, STT liên tiếp và có hình thái mã/thực thể. Lưu header_page_number/continuation_of cùng page của cell. Numeric mapping giữ IELTS/VSTEP riêng bằng các segment phân tách cột trống; nhận identity source label/acronym bằng cấu trúc chữ hoa từ nguồn, không dictionary mới.

Identity tên ưu tiên cạnh cột mã, tránh coi nhóm Toán hoặc STT là ngành. Conflict key có entity code, tránh hai chương trình cùng tên bị gộp. Cell/header bất định hoặc sai width không được dựng giá trị giả.

Thêm read-only legacy table evidence trong đúng source revision đã pin bằng index, kiểm hash/tenant/workspace/status/binding. Không đọc active_source mới thay bản index đang dùng. Index có fact_set_hash không đi qua đường recompute để tránh vượt human corrections. DB lỗi trả TABLE_EVIDENCE_UNAVAILABLE503. Conflict đánh giá theo tuple câu hỏi; không từ chối toàn bộ nguồn do bảng không liên quan có issue. Không ghi derivatives này vào knowledge_facts hoặc sửa index tại chỗ.

## Tệp thay đổi trong đợt này

- Backend knowledge: models/schemas/router; services/source_context.py, source_ingestion_service.py, generation_candidate.py, vector_generation_service.py, source_artifact.py, table_context.py, temporal_metadata.py, source_extraction.py.
- Migration: alembic/versions/20261012_fact_temporal_context.py.
- RAG: facts.py, service.py, temporal_answer.py, snapshot_fact_evidence.py; DAG query_rewrite_node.py bỏ model rewrite cho exact temporal/numeric mapping query.
- FE: types/knowledge.ts, services/knowledge-api.ts, features/knowledge/components/source-context-editor.tsx, source-detail-page.tsx.
- Tests: test_source_context_review.py; temporal_fact_contract/candidate_artifact_integration/rag fixtures và script test_temporal_rag_dag_387.py. Test empty collection được sửa fixture snapshot thật sự rỗng, không thêm AsyncMock fallback vào production để giả pass.

Versions: structured-source-v3-context-relations/layout-v7-context-relations. Stored artifact có canonical hash hợp lệ vẫn giữ nguyên; không tự upgrade published data.

## Kiểm chứng

- Regression context trước code:2fail; xuyên trang/identity trước sửa:2fail đúng thiếu facts/false conflict.
- PostgreSQL transaction rollback test context: revision mới review_required, serving pointer nguyên, bản gốc nguyên, stale edit409, review actor được ghi. Legacy evidence tests: materialized manifest không bypass, scope sai/paused/hash sai không có evidence. DB down unit case trả lỗi thật.
- Ruff full đạt; Biome4tệp UI/API/types đạt; npm run build gồm tsc đạt. Chưa browser visual QA vì dev3000/8001 chưa chạy tại lần kiểm ngoài sandbox; không tự mở helper windows/kill tiến trình.
- Final full BE:950passed,11failed,2skipped trong49,99s. 11fail khớp baseline#382: consulting export,7nhóm publishing/auth legacy403, reconciliation, fact tools, role assertion. Không sửa quyền hay thêm production mocks để che.
- Runtime DB thật + profile trợ lý admissions, chạy ngoài sandbox cho Tailscale: RAG2lượt/case, DAG1lượt/case, SSE1case. CNTT2024=16.5 và2025=21.5 đúng binding bnd_420fb9869184/source ks_rev_9f70aae2ead2/trang12, header11.2026missing không chứa21.5; IELTS6.0→9.0 trang9. DAG/SSE giữ status; done insufficient_context, không phát claim sai trước done. Đây là service-runtime E2E, không browser/auth/upload/publish E2E. Exact paths bypass cache, nên lần lặp không được gọi là cache hit test.
- Snapshot vẫn epoch10, hai index idx_rev_790c12a08c95/idx_rev_225b1211c9a2, generation vg_8b7b06c28e51. Không đổi nguồn/index published. Tests runtime tạo hội thoại/trace/usage/gap thông thường.
- Lượt runtime đầu có vLLM chat404, breaker/fallback và rewrite sai chủ đề; exact query sau sửa không cần gọi model, lượt cuối không có lỗi rewrite đó. Không khẳng định vLLM chat/provider configuration đã được chữa. Không sửa/seeding key hoặc ModelOps config trong phiên này.

## Handoff và giới hạn

Không cần reset DB hay upload lại. Mở dev bằng code mới để thử UI; muốn materialize nguồn cũ thì Ngữ cảnh → Tạo bản duyệt → duyệt → nạp staging/vector → preview/publish có chủ đích. Chưa chạy bulk draft upgrades hay restart worker/publish hộ người dùng.

Kế hoạch14 chưa hoàn tất toàn bộ: parser span/geometry tổng quát, prose facts/periods/unit normalization, mọi claim verifier, method/negation/multiturn rộng, warm cache/latency benchmarks, bulk backfill/worker rollout/full browser matrix. Các bảng không đủ invariant bị giữ unknown; không dùng tên file/năm văn bản làm năm của số liệu. Vấn đề chat404 cần kiểm ModelOps/endpoint/model riêng trước khi xác nhận toàn bộ trợ lý khỏe.
