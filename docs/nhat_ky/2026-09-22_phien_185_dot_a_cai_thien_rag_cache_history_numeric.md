# NHẬT KÝ LÀM VIỆC — PHIÊN #185
**Ngày**: 2026-09-22 | **Thời gian**: 00:30 (UTC+7)
**Tiêu đề**: Triển Khai Đợt A Đánh Giá RAG — Cache Theo History, Scoping History, Chốt Số Liệu, Rerank Timeout, Unaccent

---

## 1. Bối Cảnh
- Phiên trước đánh giá lại RAG: cache key thiếu history (`có tôi muốn` + history khác nhau trùng key), history 6 turns nhét thô gây copy đáp án cũ (câu 3 lặp câu 2), citation filter chỉ đếm từ nên số bịa lọt, rerank Cloudflare timeout 10s + fallback im lặng, query không dấu (`nganh cntt`) miss sparse.

## 2. Thay Đổi Kỹ Thuật
- `backend/app/core/redis.py`: `_make_key()` thêm hậu tố `history_hash` (`nohist` khi trống); thêm `SemanticCache.hash_history()` (SHA-256 16 ký tự của 4 turns, ổn định + honest rỗng).
- `backend/app/modules/rag/service.py`: bỏ qua cache đọc/ghi khi query <8 từ kèm history; `scope_history_by_topic()` cho prompt LLM (thay `history[-6:]` thô); chốt `verify_numeric_grounding()` sau tách gợi ý (số lạ → No-Answer + xóa citations/suggestions); cache set kèm `history_hash`.
- `backend/app/modules/rag/query_router.py`: thêm `QueryAnalysis.subject_names` dùng sẵn + `scope_history_by_topic()` (giữ turn mới nhất, turn cũ cần trùng tín hiệu; tên môn cần ngữ cảnh tổ hợp).
- `backend/app/modules/rag/citation_guard.py`: thêm `verify_numeric_grounding()` (số ≥2 chữ số, so sánh đã chuẩn hóa dấu phân cách; miễn số 1 chữ số/rỗng).
- `backend/app/modules/rag/reranker.py`: timeout Cloudflare 10s→3s; log `provider/latency_ms/in/out` cả 3 nhánh.
- `backend/app/modules/rag/retriever.py`: thêm `strip_vietnamese_accents()`, `is_unaccented_query()`, lượt ILIKE `func.unaccent()` bỏ qua êm khi thiếu extension.
- Tests mới (6): numeric grounding, unaccent helpers, scope_history drop/keep, cache history key, service skip-cache, service numeric-gate.

## 3. Kết Quả Kiểm Thử
- `uv run ruff check .`: 0 lỗi.
- Targeted 64/64 passed; full suite **368/368 passed (100%)** trong ~59s.
- Verify thủ công: key khác history → khác nhau; câu 3 scope còn turn mới nhất, rớt turn Kế toán; `29.9` bị chặn khi evidence chỉ có `24.5`; `nganh cntt` nhận diện không dấu.
- Chưa làm (đợt B/C): scorer AND facts, RRF trọng số intent, prompt tiers + ép temperature, eval online, parent-child retrieval.
