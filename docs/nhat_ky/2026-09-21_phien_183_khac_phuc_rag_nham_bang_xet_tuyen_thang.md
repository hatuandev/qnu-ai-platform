# NHẬT KÝ LÀM VIỆC — PHIÊN #183
**Ngày**: 2026-09-21 | **Thời gian**: 23:30 (UTC+7)
**Tiêu đề**: Khắc Phục RAG Trả Nhầm Bảng Xét Tuyển Thẳng Khi Hỏi Tổ Hợp Môn CNTT

---

## 1. Bối Cảnh & Vấn Đề
- Người dùng hỏi: *"bạn biết ngành công nghệ thông tin cần những môn học nào để xét tuyển không ?"*.
- Bot trả bảng *"Tên môn thi học sinh giỏi quốc gia | Tên ngành đào tạo | Mã ngành"* + *"PHỤ LỤC 1 Danh sách các ngành xét tuyển thẳng"* thay vì tổ hợp môn Trang 6 của `7480201`.
- 6 citations đều `doc_f0c1`, latency ~9906ms, đi đủ nhánh DAG `query_rewrite -> knowledge_answer -> citation_guard -> chat_output` nên DAG điều hướng đúng, lỗi nằm ở RAG retrieval + hiểu query.

## 2. Phân Tích Nguyên Nhân
- `QueryClassifier.analyze(..., admissions)` bắt đúng `entity_codes=['7480201']` nhưng `fact_attributes=[]` vì query thiếu chữ `tổ hợp` (`query_router.py` chỉ map khi có `tổ hợp`).
- Cụm *"môn học nào để xét tuyển"* overlap từ vựng mạnh với *"Môn thi HSG ... xét tuyển thẳng"* nên Dense BGE-M3 + Sparse ILIKE + reranker chấm Phụ lục 1 cao hơn Trang 6.
- `fast_rule_normalize()` chưa có paraphrase `môn học -> tổ hợp môn` (LLM few-shot đã có ví dụ đúng nhưng tầng 0ms chưa có).
- `AdmissionsRecordNormalizer` chỉ trích facts khi header có `tổ hợp/phương thức` nên facts sạch, nhưng chunks thô vẫn lẫn Phụ lục 1 và LLM không được chỉ dẫn phân biệt.

## 3. Thay Đổi Kỹ Thuật
- `backend/app/modules/workflows/nodes/query_rewrite_node.py`:
  * Thêm `_SUBJECT_COMBO_PARAPHRASES` + `_DIRECT_ADMISSION_MARKERS` + `expand_subject_combo_paraphrase()`; hook vào `fast_rule_normalize()` sau typo patterns.
  * Chống nhân đôi bằng negative lookbehind `(?<!tổ hợp\s)`, optional trailing `(?:\s+để\s+xét\s+tuyển)?` và skip-once khi đã có `tổ hợp`.
- `backend/app/modules/rag/query_router.py`:
  * Thêm `"tổ hợp"`, `"môn học"` vào `FACT_KEYWORDS_ADMISSIONS`.
  * Thêm mục 4b: `môn + (xét tuyển/ngành)` → `keywords += tổ hợp môn`, `fact_attributes += subject_combinations`, trừ khi có marker `học sinh giỏi / tuyển thẳng / ưu tiên xét tuyển`.
- Tests:
  * `tests/test_query_rewrite_node.py::test_fast_rule_normalize_subject_combo_paraphrase`
  * `tests/test_rag_generic_reuse.py::test_query_classifier_mon_hoc_maps_to_subject_combinations`
- Docs: `docs/quy_trinh/03_hybrid_rag_truy_xuat.md` (Bước 2.5), `docs/quy_trinh/04_dieu_phoi_tro_ly_dag.md` (Mục 13.1b).

## 4. Kết Quả Kiểm Thử
- `uv run ruff check .`: 0 lỗi.
- `uv run --extra dev pytest tests/test_query_rewrite_node.py tests/test_rag_generic_reuse.py tests/test_rag.py -v`: 33 passed.
- Full suite `uv run --extra dev pytest -v`: **360/360 passed (100%)** trong ~100s.
- Verify thủ công: bug query → `ngành Công nghệ thông tin cần những tổ hợp môn nào để xét tuyển`, `intent=exact_fact, codes=[7480201], attrs=[subject_combinations]`; HSG query giữ nguyên + attrs rỗng; ngày tháng giữ nguyên.
