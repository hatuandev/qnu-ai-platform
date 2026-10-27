# Nhật ký670 — Rà soát RAG backendV1 và các pattern nên bổ sung

- Ngày: 2026-10-27, Asia/Bangkok.
- User yêu cầu xem RAG cần bổ sung gì trong khi chờ prompt FE; chỉ phân tích, không triển khai.
- Áp dụng qnu-rag-pipeline và qnu-rag-evaluation; đọc mã index/search/hybrid/chunking/answer/assistant/conversation/evaluation và hợp đồng benchmark.
- Hiện có dense, PostgreSQL simple FTS/RRF/rerank ở API search/answers, table-aware chunking, follow-up rewriting và citation/source validation. Chat trợ lý chưa nối lựa chọn retrieval, vẫn dense.
- Đề xuất theo thứ tự: metadata-aware scope; parent/neighbor context trong bản xuất bản đã duyệt; answer verification; decomposition theo nhu cầu; structured/table retrieval cho đếm/tính/liệt kê. Nối retrieval policy vào snapshot assistant/hội thoại; giữ baseline và đánh giá riêng từng thay đổi.
- Python stdin cục bộ, cwd backendV1, .venv/Scripts/python.exe, exit0: nguồn tổng hợp100/câu900 có E1 hợp lệ vẫn qua parser; AssistantConfig không có retrieval fields; data_year bị extra_forbidden; paragraph có heading nhưng structure null. Đây là quan sát ranh giới hàm, không phải lỗi model/API live đã tái hiện.
- Dẫn kết quả ba câu draft Context658 đúng nhãn lịch sử; chưa có bằng chứng rerank cải thiện QNU từ mẫu đó. Không chạy benchmark mới.
- Tra nguồn chính thức Haystack sentence window/auto merging/faithfulness/decomposition, LangChain query transformations và Vanna. Notebook raw timeout; không nhận đã đọc notebook. Vanna hiện archived trên GitHub, không đề xuất dependency.
- Không đổi source BE/FE, không full tests/inference/DB, không reindex/restart/deploy/config. FE có Context668 hoàn tất đồng thời, giữ nguyên mục nhớ đó; chưa chuyển sang sửa FE.
- Kiểm tra tài liệu: UTF-8 không BOM/LF, link local, JSON và diff phạm vi.

[Báo cáo](../bao_cao/context670/REVIEW.md) · [Quan sát và hash](../bao_cao/context670/evidence.json) · [Snapshot](../memory/snapshots/2026-10-27_session_670.md).
