# Quy trình vận hành QNU AI Platform

> **Mục 1 là tài liệu sống của V1** (`backendV1/` + `frontendV2/`).
> **Mục 2 là lịch sử** của bản `backend/` trước V1, giữ nguyên để truy vết và không dùng
> để kết luận hiện trạng. Bản đồ tài liệu đầy đủ: [docs/README.md](../README.md).

---

## 1. V1 hiện hành

> Một số tài liệu trong mục này đã được dán nhãn **TÀI LIỆU LỊCH SỬ (từ 2026-11-13)** vì mô tả
> `frontendV1` hoặc harness E2E đã gỡ khỏi repo: `V1_E2E_TUNG_BUOC`, `V1_QUY_TRINH_TEST_LAI`,
> `V1_TEST_TOAN_LUONG_MODEL_QNU`, `V1_TEST_MODEL_QNU`, `V1_TEST_TB_DIEM_SAN_26`,
> `V1_TEST_OCR_QUY_CHE_363`, `V1_COMPILER_TAI_LIEU_LON`, `V1_RAG_NGU_CANH_VA_PHAM_VI`,
> 34, 35, 36, 37 và 45. Nội dung giữ nguyên để truy vết; giao diện hiện hành là `frontendV2/`.

### 1.1 Chạy, kiểm thử, đánh giá

- [Hướng dẫn chạy QNU V1](./38_huong_dan_chay_qnu_v1.md): API 8002, worker ARQ, Frontend V2 3002,
  cấu hình, migration, ModelOps và xử lý lỗi thường gặp.
- [Chạy E2E từng chặng bằng PowerShell](./V1_E2E_TUNG_BUOC.md): môi trường thử riêng, checkpoint,
  báo cáo và lệnh cho từng bước upload → hỏi đáp → purge.
- [Chạy tiếp sau khi tắt máy hoặc test mới từ đầu](./V1_QUY_TRINH_TEST_LAI.md): hai cách chạy,
  thứ tự các chặng và cấu hình đang dùng.
- [Lệnh test toàn luồng với model QNU thật](./V1_TEST_TOAN_LUONG_MODEL_QNU.md): thứ tự từ test
  model, gắn mặc định đến upload, Compiler, hỏi đáp và purge.
- [Kiểm tra model thật trên server QNU](./V1_TEST_MODEL_QNU.md): thêm provider/key/model qua
  ModelOps rồi chạy discovery/chat/embedding/rerank/OCR theo từng lệnh.
- [Kiểm tra OCR PDF scan Quy chế 363](./V1_TEST_OCR_QUY_CHE_363.md): nguồn 32 trang, kiểm mẫu
  chữ/bảng, thí nghiệm DPI riêng và lưu bản sửa chính tả.
- [Bộ câu hỏi điểm sàn 2026](./V1_TEST_TB_DIEM_SAN_26.md): phạm vi câu hỏi và cách đối chiếu.
- [Ngân sách ModelOps tự động](./V1_MODELOPS_NGAN_SACH_TU_DONG.md): thêm model không bắt nhập
  context, nguồn thông số và giới hạn ngân sách tạm tính.
- [Ngữ cảnh chunk và phạm vi có bằng chứng](./V1_RAG_NGU_CANH_VA_PHAM_VI.md): recipe có phiên
  bản, nhận diện scope, hỏi lại, glossary và kiểm chứng trước khi áp dụng.
- [MinerU làm OCR mặc định](./V1_MINERU_OCR_MAC_DINH.md): cấu hình ModelOps, PDF task,
  raw/canonical và tiếp tục rà soát hiện có.
- [Compiler với tài liệu lớn](./V1_COMPILER_TAI_LIEU_LON.md): chia phần, ngân sách và dấu vết.

### 1.2 Luồng hệ thống V1

- [47 — Hợp đồng luồng chính backend V1 cho FE mới](./47_hop_dong_luong_chinh_backend_v1.md): API tối
  giản cho tải → chuẩn bị tự động → xem/sửa → duyệt/phát hành → readiness; tách API quản trị.
- [46 — Pilot QNU V1 và đóng phạm vi bản đầu](./46_pilot_qnu_v1_va_dong_pham_vi.md): chọn đơn vị
  và người tham gia, kịch bản đo thời gian, ma trận tình huống lỗi, nghiệm thu và rollout/rollback.
- [45 — Gửi duyệt, yêu cầu sửa và danh sách “Cần xử lý”](./45_ban_giao_duyet_va_can_xu_ly_v1.md):
  submission riêng, preview/idempotency, hàng chờ đọc trạng thái thật và deep link.
- [44 — Điều hướng workspace V1](./44_dieu_huong_workspace_v1.md): bộ chọn workspace, URL gọn và
  liên kết tài liệu có kiểm quyền.
- [43 — Bóc tách tự động sau upload](./43_boc_tach_tu_dong_backend_v1.md): native-first PDF/DOCX,
  OCR khi cần, MD/JSON/ảnh, trạng thái và ZIP có kiểm quyền/hash.
- [42 — ModelOps nhà cung cấp và model](./42_modelops_nha_cung_cap_va_model.md): tạo nhà cung cấp
  → thêm khóa → thử kết nối → thêm nhiều model; giữ ID và phạm vi credential.
- [41 — API tích hợp ứng dụng](./41_api_tich_hop_ung_dung.md): cấp khóa inbound, URL tin cậy,
  phạm vi trợ lý, giới hạn gateway và lỗi.
- [40 — ModelOps nhóm khóa và model dự phòng](./40_modelops_khoa_va_du_phong.md): pool/cooldown,
  gateway retry, dự phòng theo tác vụ và lịch sử gọi có sổ sử dụng.
- [39 — ModelOps lấy danh sách và chạy thử](./39_modelops_lay_danh_sach_va_chay_thu.md): chọn
  model từ server, thử theo chức năng, đọc lỗi/độ trễ và trạng thái cấu hình cũ.
- [37 — Hỏi đáp thử, review gốc và dashboard](./37_frontend_hoi_dap_thu_review_goc_va_dashboard_qnu.md):
  POST answers theo kho, tải phản hồi review nguyên trạng, dashboard theo quyền.
- [36 — Phân trang, phạm vi tài liệu và chính tả](./36_frontend_phan_trang_pham_vi_tai_lieu_va_chinh_ta.md):
  danh sách/lịch sử qua URL, `document_ids` cùng snapshot, mở lại check hậu OCR.
- [35 — Sao lưu, dọn tệp và đánh giá RAG](./35_frontend_sao_luu_don_tep_va_danh_gia_rag.md):
  retention/verify/preview/receipt, đọc nguồn tìm kiếm, gán nhãn/so sánh/xuất báo cáo.
- [34 — Vòng đời, thay tài liệu và vận hành](./34_frontend_vong_doi_thay_the_va_van_hanh.md):
  preview/xác nhận/biên nhận, thùng rác, staged revision, trung tâm tác vụ/readiness.
- [33 — RAG policy, metadata, context và kiểm chứng](./33_rag_policy_metadata_context_va_kiem_chung_backendv1.md):
  retrieval vào chat, metadata có duyệt, context cùng bản xuất bản, judge tùy chọn.
- [32 — Duyệt review, dọn dẫn xuất, phục hồi, nghiệm thu](./32_duyet_don_du_lieu_va_phuc_hoi_backendv1.md):
  xác nhận của con người, xóa có điều kiện, restore vào đích mới, trạng thái sẵn sàng.
- [31 — Vòng đời ngược](./31_vong_doi_nguoc_backendv1.md): dừng/hủy, thùng rác/khôi phục, thay
  publication cùng index và dọn generation cũ.
- [30 — Vận hành và hybrid retrieval](./30_van_hanh_va_hybrid_backendv1.md): job/usage thật,
  phục hồi có preview, evidence backup, so sánh retrieval cùng snapshot.
- [29 — Nối hậu OCR, review và sửa Compiler](./29_noi_hau_ocr_review_va_sua_compiler_backendv1.md):
  chọn text version, review bền vững, lưu bản sửa thành run con.
- [28 — Review ngữ nghĩa Compiler](./28_review_ngu_nghia_compiler_backendv1.md): nguồn/bản nháp
  ghim, review hai chiều, báo cáo nguyên văn trước quyết định duyệt.
- [27 — Rà soát văn bản hậu OCR](./27_ra_soat_van_ban_hau_ocr_backendv1.md): gợi ý chính tả,
  sửa đoạn/ô, lưu hai tệp đồng bộ có lịch sử.
- [26 — Trợ lý và hội thoại](./26_tro_ly_va_hoi_thoai_backendv1.md): assistant config/revision,
  owner/history/sequence, follow-up và source revalidation.
- [25 — Hỏi đáp có trích dẫn](./25_hoi_dap_co_trich_dan_backendv1.md): search → evidence →
  ModelOps chat → kiểm citation/nguồn → câu trả lời.
- [24 — Index và tìm kiếm dense](./24_index_va_tim_kiem_dense_backendv1.md): publication →
  chunk/bảng có nguồn → embedding ModelOps → Qdrant generation → search/citation.
- [23 — Phiên bản và xuất bản](./23_phien_ban_va_xuat_ban_backendv1.md): document/version,
  preview, duyệt/xuất bản/thay thế/thu hồi, nguồn và receipt được ghim.
- [22 — Compiler](./22_compiler_backendv1.md): chat qua ModelOps, job bền vững, bản nháp có
  citation và bảng nguồn bất biến.
- [21 — Xử lý OCR](./21_xu_ly_ocr_backendv1.md): capacity, raw response, identity,
  heartbeat/fencing và phục hồi job.
- [20 — Kho tri thức](./20_kho_tri_thuc_backendv1.md): upload trực tiếp, ghi file nguyên vẹn,
  idempotency có title, revision và rollback bảo toàn chứng cứ.
- [19 — Workspace và ModelOps](./19_workspaces_modelops_backendv1.md): membership/role,
  grant/default theo capability, quota/usage; ngoại lệ chỉ áp dụng cho V1.

---

## 2. Lịch sử — bản `backend/` trước V1

Các tài liệu dưới đây mô tả hệ thống cũ (đã gỡ khỏi checkout): DAG engine, tool gateway,
5 trợ lý, kênh phân phối, PaddleOCR/Gemini, Structured Fact Layer. Giữ nguyên nội dung để
truy vết quyết định; **không dùng làm mô tả hiện trạng V1**.

- [01 — Khởi động nền tảng](./01_khoi_dong_nen_tang.md)
- [02 — Nạp tri thức, phân nhánh PDF Inspector/OCR & HITL](./02_nap_tri_thuc_minio.md)
- [03 — Hybrid RAG & chống bịa đặt](./03_hybrid_rag_truy_xuat.md)
- [04 — Điều phối 5 trợ lý qua DAG](./04_dieu_phoi_tro_ly_dag.md)
- [05 — Cổng công cụ & xuất bản tài liệu](./05_cong_cu_xuat_ban_tai_lieu.md)
- [06 — ModelOps, circuit breaker & dự phòng](./06_modelops_circuit_breaker.md)
- [07 — Kiểm định chất lượng Ragas TM-08](./07_kiem_dinh_chat_luong_tm08.md)
- [08 — Quản trị quy đổi điểm](./08_quan_tri_quy_doi_diem.md)
- [09 — Cấu hình Top K và chẩn đoán RAG](./09_cau_hinh_top_k_rag.md)
- [10 — Phạm vi provider, ngân sách JSON và lỗi inference](./10_rag_inference_an_toan.md)
- [11 — Bản sạch và duyệt nội dung nguồn](./11_ban_sach_va_duyet_noi_dung.md)
- [12 — Giữ cấu hình khi seed/reset](./12_seed_giu_cau_hinh.md)
- [13 — Chuẩn Markdown RAG v1.0](./13_chuan_markdown_rag_v1.md)
- [14 — Semantic selector và scope review](./14_semantic_selector_va_scope_review.md)
- [15 — Phân luồng hội thoại và phiên chat](./15_phan_luong_hoi_thoai_va_phien_chat.md)
- [16 — Trang tri thức và đọc nguồn](./16_trang_tri_thuc_va_doc_nguon.md)
- [17 — Liên kết revision và đối chiếu wiki](./17_lien_ket_revision_va_doi_chieu_wiki.md)
- [18 — Biên soạn chủ đề nhiều nguồn](./18_bien_soan_chu_de_nhieu_nguon.md)
- [Smart approval và đối chiếu nâng cao](./smart_approval.md)

---

## 3. Nguyên tắc kiểm chứng

Áp dụng [bảng kiểm chứng theo phạm vi](../../.agents/rules/verification.md) cho mọi thay đổi:
chỉ báo PASS khi đã chạy thật, lỗi nền vẫn tính FAIL, NOT RUN không phải PASS.
Quy trình memory và cập nhật tài liệu: [workflow-and-memory](../../.agents/rules/workflow-and-memory.md).
