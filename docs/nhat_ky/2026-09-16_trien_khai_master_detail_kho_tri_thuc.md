# NHẬT KÝ LÀM VIỆC — Triển Khai Master-Detail Deep Routing Cho Kho Tri Thức

- **Thời gian**: 2026-09-16 16:17 (UTC+7)
- **Mục tiêu**: Hiện thực hóa triệt để mô hình **Master-Detail Deep Routing Pattern** cho phân hệ Kho Tri Thức (`/knowledge`), tách trang chi tiết độc lập và kiểm thử tự động 100% bằng Playwright Browser Subagent.

---

## 1. Bối Cảnh & Cơ Sở Kỹ Thuật

Trước đây, khi người dùng click vào một Bộ sưu tập trong trang Kho Tri Thức, giao diện chỉ thực hiện chuyển tab nội bộ (`setActiveTab("documents")`) trên cùng một trang ("Monolithic Tabbed Anti-pattern"). Điều này khiến:
- Giao diện bị chật hẹp, không có không gian cho các tính năng sâu (RAG Retrieval Sandbox, RAG Specs, MinIO S3 inspector, Linked Assistants).
- Không hỗ trợ Deep Linking (F5 bị mất ngữ cảnh bộ sưu tập đang xem).
- Vi phạm quy tắc UI mở tại Mục 4.5 của [`AGENTS.md`](file:///d:/DuAnPhanMem/qnu-ai-platform/AGENTS.md).

---

## 2. Các Thay Đổi Kỹ Thuật Chi Tiết

1. **Tạo trang chi tiết độc lập [`frontend/src/pages/collection-detail-page.tsx`](file:///d:/DuAnPhanMem/qnu-ai-platform/frontend/src/pages/collection-detail-page.tsx)**:
   - Breadcrumb: Nút quay lại `ArrowLeft` kèm đường dẫn `Kho Tri Thức / [Tên Bộ Sưu Tập]`.
   - Action Toolbar: Nút "Đồng Bộ Vector" (Re-index) có animation và toast phản hồi; Nút "Nạp Văn Bản Mới" mở Ingestion Wizard modal đã bind cứng `collectionId`.
   - Layout 2 cột chuyên sâu (2/3 & 1/3):
     - Cột trái: Bảng danh mục tài liệu con kèm tìm kiếm nhanh; Khung **RAG Retrieval Sandbox** thử nghiệm truy vấn Hybrid RRF (k=60) + Cross-Encoder trả kết quả 42ms; Dialog Chunks Inspector xem chi tiết đoạn trích mẫu và link tải file gốc MinIO.
     - Cột phải: RAG Specs (Qdrant `col_{code}_dense`, Chunking strategy, OCR profile, PDF Inspector native text 10-30ms, MinIO storage prefix `s3://qnu-knowledge-raw/{code}/`); Trợ lý AI liên kết (`/chat`); Quality benchmark (Ragas Faithfulness 0.96, Context Precision 0.92).
2. **Refactor [`frontend/src/pages/knowledge-page.tsx`](file:///d:/DuAnPhanMem/qnu-ai-platform/frontend/src/pages/knowledge-page.tsx)**:
   - Chuyển thành Master/List View tập trung: 3 thẻ KPI, tìm kiếm và lọc theo thuật toán phân mảnh.
   - Grid cards các bộ sưu tập hiển thị thoáng đãng, sang trọng; click card chuyển hướng URL sang `/knowledge/collections/:id`.
   - Đọc URL state và tự động render `<CollectionDetailPage />` khi có `collectionId`.
3. **Cập nhật định tuyến trong [`frontend/src/App.tsx`](file:///d:/DuAnPhanMem/qnu-ai-platform/frontend/src/App.tsx)**:
   - Hỗ trợ route `/knowledge` và `/knowledge/collections/:id`, truyền `currentPath` và `onNavigate={handleNavigate}`.

---

## 3. Kết Quả Kiểm Thử (Verification)

- **`npm run lint`**: 0 errors (Biome check 60 files pass).
- **`npm run typecheck`**: 0 errors (TypeScript compile pass).
- **`npm run build`**: Thành công đóng gói Vite production bundle trong 7.94s.
- **Kiểm thử tự động Playwright Browser Subagent**:
  - 10/10 test cases PASS hoàn toàn.
  - Video ghi hình: `test_knowledge_deep_routing_1789549700688.webp`.
  - Nghiệm thu Deep Linking và Back Navigation thành công.
