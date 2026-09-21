# NHẬT KÝ LÀM VIỆC — PHIÊN #187
**Ngày**: 2026-09-22 | **Thời gian**: 02:30 (UTC+7)
**Tiêu đề**: Triển Khai Đợt C Đánh Giá RAG — Parent-Child, Multi-Query, Drift Dashboard

---

## 1. Bối Cảnh
- Đợt A khóa lỗi đúng/sai (cache, history, số liệu, rerank, unaccent); Đợt B nâng relevance (rank facts, RRF weights, prompt tiers, vote). Đợt C xử lý recall sâu (ngữ cảnh kề, biến thể truy vấn) và vòng phản hồi vận hành (trend/drift).

## 2. Thay Đổi Kỹ Thuật
- **C1** `rag/retriever.py::expand_with_neighbors()` (kề `chunk_index`, fallback `page_number`, tối đa 2 chunks, nhãn prompt-only) + nối vào `rag/service.py` (`BỐI CẢNH MỞ RỘNG`, cắt 1000 ký tự/đoạn).
- **C2** `rag/fusion.py` (`_merge_ranked_list` + `extra_lists` chiết khấu), `rag/retriever.py::retrieve(..., sparse_variants)` (song song, top_k/2, weight 0.5), `rag/service.py` dựng `keyword_query` từ mã/môn/từ khóa dài.
- **C3** conversations: `feedback_trend` (buckets Python, clamp 1-90 ngày, cap 5000) + `feedback_samples` (mới nhất, clamp limit) + 2 endpoints; frontend `feedback-panel.tsx` (KPI, thanh trend, bảng down) gắn tab mới trên `/evaluation`; `ChatMessage.onFeedback` đã nối từ phiên #186.
- Tests mới (5): neighbors + graceful, fusion variants, service variants + neighbor prompt, trend/samples (kể cả clamp và rỗng).

## 3. Kết Quả Kiểm Thử
- Backend: `ruff` 0 lỗi; Pytest **377/377 passed (100%)**.
- Frontend: Biome 169 files 0 lỗi; `tsc` 0 lỗi; Vite build 7.97s thành công.
- Kết thúc chuỗi A→B→C: hết backlog đánh giá RAG đã nêu; bước tiếp theo đề xuất là đo TM-08 lại trên live và đọc `/feedback/stats` sau 1-2 tuần vote.
