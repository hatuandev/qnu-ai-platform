# NHẬT KÝ LÀM VIỆC — PHIÊN #184
**Ngày**: 2026-09-21 | **Thời gian**: 23:55 (UTC+7)
**Tiêu đề**: Parser Gợi Ý Chịu Lỗi JSON Inline + Tra Cứu Ngược Tổ Hợp Môn Theo Tên Môn

---

## 1. Bối Cảnh & Vấn Đề
- Hội thoại 3 lượt: câu 1 CNTT đã đúng sau fix #183 nhưng lộ raw `[GỢI Ý]: ["...","..."]` và chips fallback tĩnh; câu 2 phương thức đúng; câu 3 `các ngành xét tuyển tổ hợp môn Toán, Tiếng Anh, Hóa học` lặp nguyên đáp án câu 2 (5 phương thức) thay vì liệt kê ngành.
- Reproduce: `extract_suggested_questions()` với chuỗi JSON 1 dòng trả `([], text)` do regex đòi `\n` sau marker; `analyze(câu 3)` cho `codes=[], attrs=[subject_combinations]`, keywords chung; ILIKE dùng 3 token đầu `các/ngành/xét`.

## 2. Thay Đổi Kỹ Thuật
- `backend/app/modules/rag/composer.py`:
  * Regex `_EXPLICIT_SUGGESTION_BLOCK` kết thúc `\s*` (nhận cùng dòng).
  * Thêm `_clean_suggestion_candidate()`, `_is_question_like()`, `_extract_candidates_from_block()` (quoted-first cho JSON inline, bullet/`;` sau đó); marker rỗng bị lột thay vì rò raw.
- `backend/app/modules/rag/query_router.py`:
  * Thêm `QueryAnalysis.subject_names` + `SUBJECT_PATTERNS` (tiếng anh/vật lý/hóa/sinh/văn/sử/địa/tin/công nghệ...), gate ngữ cảnh `tổ hợp` hoặc `môn + xét tuyển`, loại HSG/tuyển thẳng và đại từ `anh` trần.
- `backend/app/modules/rag/retriever.py`:
  * Thêm `ILIKE_STOP_SYLLABLES` + `select_ilike_tokens()` (regex `\w+`, bỏ từ chung, lấy tới 6 token đặc thù); ILIKE OR dùng toàn bộ tokens thay vì 3 đầu.
- Tests mới: `test_extract_suggested_questions_parses_inline_json_array_without_leak`, `test_select_ilike_tokens_prefers_distinctive_subject_tokens`, `test_query_classifier_extracts_subjects_for_reverse_combo_lookup`.
- Docs: `03` (tra cứu ngược + token), `04` (Mục 13.1c parser).

## 3. Kết Quả Kiểm Thử
- `uv run ruff check .`: 0 lỗi.
- Targeted 38 passed; full suite **363/363 passed (100%)** trong ~54s.
- Verify: JSON inline → 2 suggestions + body sạch marker; câu 3 → `subjects=[tiếng anh, hóa, toán]`, tokens `[toán, tiếng, anh, hóa]`; đại từ/HSG/rỗng an toàn.
- Lưu ý: đáp án câu 1 (5 combos toàn Toán-Anh-X) và nội dung citations câu 3 trên live cần đối soát thêm với facts Trang 6 sau khi seed lại.
