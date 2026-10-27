# HỆ THỐNG QUY TRÌNH VẬN HÀNH NỀN TẢNG (PROCESS DIRECTORY)
## Nền Tảng Trí Tuệ Nhân Tạo Trường Đại Học Quy Nhơn (QNU AI Platform)

Thư mục này chứa tài liệu đặc tả kỹ thuật chi tiết của toàn bộ các quy trình nghiệp vụ, vòng đời vận hành và luồng luân chuyển dữ liệu của hệ thống.

---

## 🗺️ Bản Đồ Điều Hướng Các Quy Trình

- [38 — Hướng dẫn chạy QNU V1](./38_huong_dan_chay_qnu_v1.md): ba tiến trình API/worker/FE, cấu hình, migration, admin local, ModelOps và xử lý lỗi.

- [37 — Frontend hỏi đáp thử, review gốc và dashboard QNU](./37_frontend_hoi_dap_thu_review_goc_va_dashboard_qnu.md): POST answers theo kho, tải phản hồi review nguyên trạng và dashboard dữ liệu thật theo workspace/quyền.

- [36 — Frontend phân trang, phạm vi tài liệu và chính tả](./36_frontend_phan_trang_pham_vi_tai_lieu_va_chinh_ta.md): danh sách/lịch sử qua URL, document_ids cùng snapshot và mở lại check hậu OCR bằng GET.

- [35 — Frontend sao lưu, dọn tệp và đánh giá RAG](./35_frontend_sao_luu_don_tep_va_danh_gia_rag.md): retention/verify/preview/receipt, đọc nguồn tìm kiếm và gán nhãn/so sánh/xuất báo cáo cùng snapshot.

- [34 — Frontend vòng đời, thay tài liệu và vận hành](./34_frontend_vong_doi_thay_the_va_van_hanh.md): preview/xác nhận/biên nhận, thùng rác, staged revision và trung tâm tác vụ/readiness theo quyền.

- [33 — RAG policy, metadata, context và kiểm chứng backendV1](./33_rag_policy_metadata_context_va_kiem_chung_backendv1.md): retrieval vào chat, metadata có duyệt, context cùng bản xuất bản và judge tùy chọn.

- [32 — Duyệt review, dọn dẫn xuất, phục hồi và nghiệm thu backendV1](./32_duyet_don_du_lieu_va_phuc_hoi_backendv1.md): xác nhận của con người, xóa có điều kiện, restore vào đích mới và trạng thái sẵn sàng có bằng chứng.

- [31 — Vòng đời ngược backendV1](./31_vong_doi_nguoc_backendv1.md): dừng/hủy, thùng rác/khôi phục, thay publication cùng index và dọn generation cũ có xác nhận.

- [30 — Vận hành và hybrid retrieval backendV1](./30_van_hanh_va_hybrid_backendv1.md): job/usage thật, phục hồi có preview, evidence backup và so sánh retrieval cùng snapshot.

- [29 — Nối hậu OCR, review và sửa Compiler backendV1](./29_noi_hau_ocr_review_va_sua_compiler_backendv1.md): chọn text version, review bền vững và lưu bản sửa có preview thành run con.

- [28 — Review ngữ nghĩa Compiler backendV1](./28_review_ngu_nghia_compiler_backendv1.md): nguồn/bản nháp ghim, review hai chiều và báo cáo nguyên văn trước quyết định duyệt.

- [27 — Rà soát văn bản hậu OCR backendV1](./27_ra_soat_van_ban_hau_ocr_backendv1.md): gợi ý chính tả, sửa đoạn/ô và lưu hai tệp đồng bộ có lịch sử.

- [26 — Trợ lý và hội thoại backendV1](./26_tro_ly_va_hoi_thoai_backendv1.md): assistant config/revision, owner/history/sequence, follow-up và source revalidation.

- [25 — Hỏi đáp có trích dẫn backendV1](./25_hoi_dap_co_trich_dan_backendv1.md): search → evidence → ModelOps chat → kiểm citation/nguồn → câu trả lời.

- [24 — Index và tìm kiếm dense backendV1](./24_index_va_tim_kiem_dense_backendv1.md): publication → chunk/bảng có nguồn → ModelOps embedding → Qdrant generation → search/citation.

- [23 — Phiên bản và xuất bản backendV1](./23_phien_ban_va_xuat_ban_backendv1.md): document/version, preview, duyệt/xuất bản/thay thế/thu hồi, nguồn và receipt được ghim.

- [22 — Compiler backendV1](./22_compiler_backendv1.md): chat qua ModelOps, job bền vững, bản nháp có citation và bảng nguồn bất biến.

- [21 — Xử lý OCR backendV1](./21_xu_ly_ocr_backendv1.md): capacity, raw response, identity, heartbeat/fencing và phục hồi job.

- [20 — Kho tri thức backendV1](./20_kho_tri_thuc_backendv1.md): upload trực tiếp, ghi file nguyên vẹn, idempotency có title, revision và rollback bảo toàn chứng cứ.

- [19 — Workspace và ModelOps backendV1](./19_workspaces_modelops_backendv1.md): membership/role, grant/default theo capability, quota/usage; ngoại lệ chỉ v1, giữ backend cũ.

- [18 — Biên soạn chủ đề nhiều nguồn](./18_bien_soan_chu_de_nhieu_nguon.md): compiler
  có proof/review ledger, intent/idempotency, Storage bất biến, decision có quyền và
  stale/revocation; không tự áp dụng vào RAG hoặc publication.

- [17 — Liên kết, revision và đối chiếu Trang tri thức](./17_lien_ket_revision_va_doi_chieu_wiki.md):
  liên quan/backlinks theo snapshot, reuse nguồn tương thích và Advanced Review có quyền.

- [16 — Trang tri thức và đọc nguồn có giới hạn](./16_trang_tri_thuc_va_doc_nguon.md):
  biên soạn nguồn/thực thể/khái niệm, vai trò năm, nguồn nguyên văn và điều hướng
  theo snapshot đã xuất bản; model động, budget, cache và trạng thái lỗi.

- [15 — Phân luồng hội thoại và phiên chat](./15_phan_luong_hoi_thoai_va_phien_chat.md): social/meta, contextual rewrite, quyền debug, continuation capability và tách phiên public/widget.

- [Nạp tài liệu tự động và đối chiếu nâng cao](./smart_approval.md): ba trạng thái chất lượng, nạp vector tách publication; Smart Approval, audit và transaction trong chế độ nâng cao.

- [14 — Semantic selector và scope review](./14_semantic_selector_va_scope_review.md):
  selector v1/v2, owner do registry xác thực, đối chiếu toàn nguồn và tập đích,
  quyết định theo issue/proposal hash và checkpoint kiểm chứng có người duyệt.

- [13 — Chuẩn Markdown RAG v1.0](./13_chuan_markdown_rag_v1.md): file chuẩn và mẫu
  dùng lại, lõi Universal + quy tắc dữ liệu chọn lọc + chỉ mục dẫn xuất; parser
  có đề xuất ngữ nghĩa qua ModelOps và đối chiếu trước khi áp dụng vào bản nháp (11.6);
  snapshot annotation theo revision, replay và gói xuất có sidecar tại 11.7;
  giới hạn nguồn đã đối chiếu, strict/evaluation và runner ModelOps tại 11.8;
  context có cấu trúc, selectors/exact evidence binding và bounded expansion tại 11.9;
  vòng đời issue/decisions, snapshot hash tương thích và deadline/accounting chung tại 11.10;
  JSON output contract/capability/strict parser và bounded format retry tại 11.11;
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
