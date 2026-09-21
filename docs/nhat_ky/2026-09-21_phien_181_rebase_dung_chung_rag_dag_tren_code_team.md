# NHẬT KÝ LÀM VIỆC — PHIÊN #181
**Ngày**: 2026-09-21 | **Thời gian**: 17:10 (UTC+7)
**Tiêu đề**: Rebase Dùng Chung RAG Hybrid & DAG Lên Code Team (sessions 175-180)

> Phiên này rebase công việc generic #175 local lên code team mới pull (sessions #175-180 của team: greeting routing, zero-emoji, Gemini 2.5/Gemma 4, focus guardrail, entity augmentation, suggestion chips). Giữ đầy đủ tính năng team, hợp nhất phần dùng chung cho trợ lý mới.

---

## 1. Bối Cảnh & Yêu Cầu

Người dùng yêu cầu cải thiện chất lượng RAG hybrid và DAG workflows để có thể dùng chung cho mọi trợ lý AI khi tạo mới trợ lý nào đó vẫn xử lý tốt, không bị nhiễm hardcode tuyển sinh.

Khảo sát cho thấy 4 điểm nghẽn dùng chung:
- `query_router.py` chỉ biết mã ngành/IELTS/kế hoạch, thiếu library/drafting/question_bank.
- `service.py` + `citation_guard.py` gán cứng hotline 0256.3846.156 và keywords triệu/học phí/điểm chuẩn.
- `rag_answer_node.py` mặc định `col_admissions`, `llm_generate_node.py` thiếu try/except.
- Không có template DAG generic, `fork_workflow` chỉ clone mà không tiêm bindings.

---

## 2. Chi Tiết Thực Hiện

### 2.1. RAG Hybrid Dùng Chung
- [`backend/app/modules/rag/query_router.py`](file:///d:/DuAnPhanMem/qnu-ai-platform/backend/app/modules/rag/query_router.py): Bổ sung packs library/drafting/question_bank/regulations, `GENERIC_FACT_KEYWORDS`, regex `RE_DECISION_CODE/RE_MONEY/RE_YEAR`, registry `FACT_KEYWORD_PACKS`, API `analyze(query, module_code="general")` tương thích ngược.
- [`backend/app/modules/rag/citation_guard.py`](file:///d:/DuAnPhanMem/qnu-ai-platform/backend/app/modules/rag/citation_guard.py): Bổ sung template library/drafting/question_bank, `EVIDENCE_KEYWORDS` generic, `get_no_answer_response(module_code, assistant_name)` sinh fallback nêu tên trợ lý mới.
- [`backend/app/modules/rag/service.py`](file:///d:/DuAnPhanMem/qnu-ai-platform/backend/app/modules/rag/service.py): Thêm `MODULE_CONTACT_HINTS`, `build_generic_system_instruction()`, `is_refusal_answer()` phi thiên vị domain, bỏ heuristic admissions, truyền `module_code` vào classifier.
- [`backend/app/modules/rag/schemas.py`](file:///d:/DuAnPhanMem/qnu-ai-platform/backend/app/modules/rag/schemas.py): `AskRequest.module_code` mặc định `general`.
- [`backend/app/modules/rag/composer.py`](file:///d:/DuAnPhanMem/qnu-ai-platform/backend/app/modules/rag/composer.py): Mở rộng RE_TABLE/TIMELINE/CHECKLIST cho sách/giáo trình/quyết định/ma trận.

### 2.2. DAG Workflows Dùng Chung
- [`backend/app/modules/workflows/nodes/query_rewrite_node.py`](file:///d:/DuAnPhanMem/qnu-ai-platform/backend/app/modules/workflows/nodes/query_rewrite_node.py): `fast_rule_normalize(text, extra_acronyms)` đọc `config.custom_acronyms` từng trợ lý.
- [`backend/app/modules/workflows/nodes/rag_answer_node.py`](file:///d:/DuAnPhanMem/qnu-ai-platform/backend/app/modules/workflows/nodes/rag_answer_node.py): Fail-safe collection (profile → config → `col_{module}` chính thức), thiếu thì ném `workflow_missing_collection` 422; module fallback `general`.
- [`backend/app/modules/workflows/nodes/llm_generate_node.py`](file:///d:/DuAnPhanMem/qnu-ai-platform/backend/app/modules/workflows/nodes/llm_generate_node.py): Bọc generate trong try/except ném `llm_generation_failed` 502.
- [`backend/app/modules/workflows/service.py`](file:///d:/DuAnPhanMem/qnu-ai-platform/backend/app/modules/workflows/service.py): `_inject_assistant_bindings()` + `fork_workflow(..., module_code, collection_id, system_prompt, rewrite_instruction)`; `sync_default_workflows` bỏ qua file `_*.json`.
- [`configs/workflows/_base-assistant.v1alpha1.json`](file:///d:/DuAnPhanMem/qnu-ai-platform/configs/workflows/_base-assistant.v1alpha1.json): Template 8 nodes chuẩn, `module_code=general`, pass compiler validation.
- [`backend/tests/test_rag_generic_reuse.py`](file:///d:/DuAnPhanMem/qnu-ai-platform/backend/tests/test_rag_generic_reuse.py): 9 tests mới phủ router generic, no-answer generic, system instruction, refusal, custom acronyms, fork injection, base template, fail-closed.
- [`backend/tests/test_node_catalog.py`](file:///d:/DuAnPhanMem/qnu-ai-platform/backend/tests/test_node_catalog.py): Nới `==13` thành `>=13` cho manifest tương lai.

### 2.3. Đồng Bộ Tài Liệu Quy Trình
- Bổ sung Bước 11 trong [`docs/quy_trinh/03_hybrid_rag_truy_xuat.md`](../quy_trinh/03_hybrid_rag_truy_xuat.md).
- Bổ sung Mục 14 trong [`docs/quy_trinh/04_dieu_phoi_tro_ly_dag.md`](../quy_trinh/04_dieu_phoi_tro_ly_dag.md).

---

## 3. Kết Quả Kiểm Thử

- **Backend Linter**: `uv run ruff check .` → **0 lỗi**.
- **Backend Tests**: `uv run --extra dev pytest -q` → **350/350 passed (100%)** trong 105s (bao gồm 9 tests generic mới).
- **Frontend**: Không đổi code Frontend, không cần build lại.
- **Template validation**: `_base-assistant` pass `workflow_compiler.validate` (True, 0 issues).
