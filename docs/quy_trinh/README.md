# HỆ THỐNG QUY TRÌNH VẬN HÀNH NỀN TẢNG (PROCESS DIRECTORY)
## Nền Tảng Trí Tuệ Nhân Tạo Trường Đại Học Quy Nhơn (QNU AI Platform)

Thư mục này chứa tài liệu đặc tả kỹ thuật chi tiết của toàn bộ các quy trình nghiệp vụ, vòng đời vận hành và luồng luân chuyển dữ liệu của hệ thống.

---

## 🗺️ Bản Đồ Điều Hướng Các Quy Trình

- [13 — Chuẩn Markdown RAG v1.0](./13_chuan_markdown_rag_v1.md): file chuẩn và mẫu
  dùng lại, lõi Universal + quy tắc dữ liệu chọn lọc + chỉ mục dẫn xuất; parser
  có đề xuất ngữ nghĩa qua ModelOps và đối chiếu trước khi áp dụng vào bản nháp (11.6);
  snapshot annotation theo revision, replay và gói xuất có sidecar tại 11.7;
  giới hạn nguồn đã đối chiếu, strict/evaluation và runner ModelOps tại 11.8;
  context có cấu trúc, selectors/exact evidence binding và bounded expansion tại 11.9;
  vòng đời issue/decisions, snapshot hash tương thích và deadline/accounting chung tại 11.10;
  DOCX/PDF mới có luồng serving chuẩn có duyệt (phiên526), revision cũ không tự chuyển; không nạp nguyên tài
  liệu chuẩn này làm kiến thức.

- [12 — Seed giữ cấu hình](./12_seed_giu_cau_hinh.md): capture mã hóa qua StorageDriver,
  preview và restore vào cấu hình rỗng trước bootstrap; không tự reset hoặc hồi sinh publication.

- [11 — Bản sạch và duyệt nội dung nguồn](./11_ban_sach_va_duyet_noi_dung.md): chuẩn hóa
  bảo toàn cấu trúc, preview/diff trong Studio, actor/lý do và revision chờ duyệt;
  chunk theo cấu trúc, bundle nguồn/facts/vector và xuất bản/rollback có đối soát.

- [10 — Inference RAG an toàn](./10_rag_inference_an_toan.md): danh sách provider máy
  chủ, bảo toàn ngân sách JSON, log metadata và một retry dùng chung có giới hạn.

- [09 — Cấu hình Top K và chẩn đoán RAG](./09_cau_hinh_top_k_rag.md): cấu hình
  đối chứng/tùy chỉnh, tìm kiếm không sinh đáp án và giới hạn phép đo.

- [08 — Quản trị quy đổi điểm có kiểm chứng](./08_quan_tri_quy_doi_diem.md): xem nguồn,
  tính thử, duyệt/kích hoạt/thu hồi và runtime chỉ dùng quy tắc đang hoạt động.

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
