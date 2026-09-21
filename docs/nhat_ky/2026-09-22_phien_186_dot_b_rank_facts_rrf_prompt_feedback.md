# NHẬT KÝ LÀM VIỆC — PHIÊN #186
**Ngày**: 2026-09-22 | **Thời gian**: 01:30 (UTC+7)
**Tiêu đề**: Triển Khai Đợt B Đánh Giá RAG — Rank Facts, RRF Trọng Số, Prompt Tầng, Eval Online

---

## 1. Bối Cảnh
- Đợt A đã khóa cache/history/số liệu/rerank/unaccent. Đợt B xử lý 4 mục còn lại: facts OR-match cắt mất đáp án đúng, RRF cào bằng 2 nhánh, prompt trộn tiers + temperature cao cho fact, vote 👍/👎 chỉ nằm local state.

## 2. Thay Đổi Kỹ Thuật
- **B1** `rag/facts.py`: `count_subject_matches()` (quét value, regex biên từ) + `lookup_facts(..., subject_names)` over-fetch ×3, sort, cắt limit; `service.py` truyền `analysis.subject_names`.
- **B2** `rag/fusion.py` (`dense_weight/sparse_weight`), `rag/retriever.py` (`retrieve()` nhận và chuyển tiếp), `rag/service.py` chọn (1.0/1.2), (1.0/1.0), (1.2/0.8) theo EXACT/MIXED/NARRATIVE + log policy.
- **B3** `rag/service.py`: fact-query tách TẦNG 1/2/3 + quy tắc xung đột, nhãn history, `temperature=min(req,0.2)` cho cả primary và fallback.
- **B4** conversations: model `ConversationFeedbackModel` + migration `20260922_conversation_feedback` (đã `upgrade head`, `alembic check` sạch); schemas vote/stats; service `record_feedback` (404 thread lạ) + `feedback_stats` (up-rate); router 2 endpoints; frontend `recordFeedbackVote` + `onFeedback` trong `ChatMessage` + `handleFeedback` best-effort trong `chat-studio-page.tsx`.
- Tests mới (7): RRF weights, subject match, lookup rank, intent weights + temperature tiers, scope giữ nguyên, feedback vote/stats/404/empty.

## 3. Kết Quả Kiểm Thử
- Backend: `ruff` 0 lỗi; Pytest **373/373 passed (100%)**; `alembic check` sạch.
- Frontend: Biome 168 files 0 lỗi; `tsc` 0 lỗi; Vite build 9.94s thành công.
- Lưu ý live: backend + frontend đều cần deploy lại; vote cũ (local state) không migrate được; theo dõi `up_rate` qua `/feedback/stats` và log `Numeric grounding failed`.
