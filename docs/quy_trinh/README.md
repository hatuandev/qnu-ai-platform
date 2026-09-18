# HỆ THỐNG QUY TRÌNH VẬN HÀNH NỀN TẢNG (PROCESS DIRECTORY)
## Nền Tảng Trí Tuệ Nhân Tạo Trường Đại Học Quy Nhơn (QNU AI Platform)

Thư mục này chứa tài liệu đặc tả kỹ thuật chi tiết của toàn bộ các quy trình nghiệp vụ, vòng đời vận hành và luồng luân chuyển dữ liệu của hệ thống.

---

## 🗺️ Bản Đồ Điều Hướng Các Quy Trình

| STT | Tên Quy Trình Nghiệp Vụ | Tệp Tài Liệu Chi Tiết | Trọng Tâm Kỹ Thuật |
| :---: | :--- | :--- | :--- |
| **01** | **Khởi Động & Vòng Đời Nền Tảng** | [`01_khoi_dong_nen_tang.md`](./01_khoi_dong_nen_tang.md) | Docker Compose, thứ tự nạp container, healthchecks, kết nối Connection Pool |
| **02** | **Nạp Tri Thức, Phân Nhánh OCR & Đối Soát HITL MinIO** | [`02_nap_tri_thuc_minio.md`](./02_nap_tri_thuc_minio.md) | Smart Recommendation $\rightarrow$ MinIO/Local $\rightarrow$ PyMuPDF/Mistral OCR $\rightarrow$ Chunker $\rightarrow$ Studio HITL Review $\rightarrow$ Approve Qdrant + Postgres FTS |
| **03** | **Truy Vấn Hybrid RAG & Chống Bịa Đặt** | [`03_hybrid_rag_truy_xuat.md`](./03_hybrid_rag_truy_xuat.md) | Structured Fact Layer, RRF $k=60$, Reranker, Citation Guardrail, Hotline Fallback |
| **04** | **Điều Phối 05 Trợ Lý AI (DAG Engine)** | [`04_dieu_phoi_tro_ly_dag.md`](./04_dieu_phoi_tro_ly_dag.md) | DAG Engine, Node Handlers, Word Boundary Safe Route, Human Approval Checkpoint |
| **05** | **Cổng Công Cụ & Xuất Bản Tài Liệu** | [`05_cong_cu_xuat_ban_tai_lieu.md`](./05_cong_cu_xuat_ban_tai_lieu.md) | Function Calling, Xuất Word NĐ 30, Excel Bloom, Lưu MinIO, Gotenberg Preview |
| **06** | **ModelOps Resilience & Fallback** | [`06_modelops_circuit_breaker.md`](./06_modelops_circuit_breaker.md) | Circuit Breaker 3 trạng thái, Dynamic Fallback Cascade, Quota Guard & CostTracker |
| **07** | **Kiểm Định Chất Lượng Ragas TM-08** | [`07_kiem_dinh_chat_luong_tm08.md`](./07_kiem_dinh_chat_luong_tm08.md) | Bộ 100 câu benchmark, Faithfulness $\ge 0.90$, Relevance $\ge 0.85$, Precision $\ge 0.80$ |

---

## 📌 Nguyên Tắc Vận Hành Bắt Buộc Của Nền Tảng
1. **MinIO-First**: Mọi tệp tài liệu do người dùng tải lên và mọi sản phẩm do AI sinh ra (Word/Excel) đều phải được lưu trữ an toàn trên MinIO Object Storage trước khi xử lý.
2. **Zero-Hallucination**: Các thông số chính xác (điểm chuẩn, học phí, chỉ tiêu) bắt buộc phải tra cứu từ Structured Fact Layer trước khi kích hoạt tìm kiếm ngữ nghĩa.
3. **Resilience 24/7**: Mọi kết nối LLM ngoại vi đều được bảo vệ bởi Circuit Breaker và cơ chế Fallback tự động sang Google Gemini hoặc Local vLLM.
