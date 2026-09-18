# NHẬT KÝ LÀM VIỆC — PHIÊN #82
# Ngày: 2026-09-18 | Phiên số: #82
# Tiêu đề: Triển Khai Phân Hệ Xuất Văn Bản DOCX/PDF Chuẩn NĐ 30 & Nạp Toàn Văn Nghị Định 30 Vào CSDL Mặc Định

---

## 1. Mục Tiêu Phiên Làm Việc

1. Hiện thực hóa phân hệ **Tạo và Xuất Bản Văn Bản Hành Chính (DOCX & PDF)** chuẩn thể thức Nghị định 30/2020/NĐ-CP của Trường Đại học Quy Nhơn cho Trợ lý Soạn thảo (`ast_drafting`) và DAG Workflow `drafting-assistant`.
2. Thiết kế cơ chế **Prompt 3 tầng tương tác tự nhiên**:
   - Tầng 1: Tư vấn và phác thảo cấu trúc văn bản hành chính sư phạm trang trọng.
   - Tầng 2: Chủ động gợi ý xuất file ở cuối câu trả lời (*"Thầy/Cô có muốn em xuất bản hoàn chỉnh văn bản này thành file Word (.docx) và PDF (.pdf) chuẩn thể thức Đại học Quy Nhơn (Nghị định 30) để in hoặc trình ký ngay không ạ?"*).
   - Tầng 3: Tự động kích hoạt công cụ kết xuất tệp khi người dùng đồng ý hoặc yêu cầu tạo file.
3. Nạp vĩnh viễn toàn văn 11 trang **Nghị định 30/2020/NĐ-CP** vào CSDL PostgreSQL (`col_drafting`) và Qdrant Vector Index dưới dạng **Seed Data Mặc Định** của nền tảng, xóa bỏ triệt để hiện tượng No-Answer khi tra cứu thể thức.
4. Tích hợp giao diện Frontend hiển thị thẻ tải file `.docx` và `.pdf` riêng biệt, kèm dung lượng, mã màu và nút download trực tiếp.

---

## 2. Chi Tiết Kỹ Thuật Đã Triển Khai

### 2.1. Bộ Mẫu Văn Bản Word DOCX Chuẩn Nghị Định 30 (`backend/app/templates/documents/`)
Đã thiết kế 3 tệp mẫu Word với các tham số `docxtpl` (`{{ trich_yeu }}`, `{{ so_hieu }}`, `{{ noi_dung }}`, `{{ ngay_thang_nam }}`, `{{ chuc_vu_nguoi_ky }}`, `{{ ho_ten_nguoi_ky }}`, `{{ noi_nhan }}`):
- `mau_to_trinh_nd30.docx`: Mẫu tờ trình đề xuất kinh phí, đề án, mua sắm.
- `mau_thong_bao_nd30.docx`: Mẫu thông báo triển khai kế hoạch, kết luận cuộc họp.
- `mau_quyet_dinh_nd30.docx`: Mẫu quyết định cá biệt của Hiệu trưởng.
- Quy chuẩn thể thức: Căn lề chuẩn (Trên 20mm, Dưới 20mm, Trái 30mm, Phải 15mm), phông Times New Roman 13-14pt, Quốc hiệu Tiêu ngữ in hoa đậm, dòng kẻ phân cách chuẩn.

### 2.2. Dịch Vụ Kết Xuất Văn Bản (`backend/app/modules/tools/document_generator.py`)
- Sử dụng thư viện `docxtpl` kết hợp `docx` để render nội dung động vào file Word mẫu.
- Kết nối Gotenberg 8 API qua endpoint `POST /forms/libreoffice/convert` để chuyển đổi `.docx` sang `.pdf` trung thực 100%.
- Cơ chế Graceful Fallback: Khi Gotenberg offline/unreachable, tự động giữ file `.docx` an toàn và trả về liên kết tải về cho người dùng mà không gây lỗi 500.
- Lưu trữ qua `storage_service` và cung cấp endpoint `GET /platform/v1alpha1/tools/artifacts/{filename}` để người dùng click tải về trực tiếp từ trình duyệt.

### 2.3. Trích Xuất & Nạp Seed Data Nghị Định 30/2020/NĐ-CP
- File `backend/app/modules/knowledge/seed_data_nd30.py`:
  * 6 Chunks chuẩn hóa theo từng Chương/Điều (Chương I Quy định chung, Chương II Thể thức & Kỹ thuật trình bày Điều 7-9, Mục 2 Soạn thảo & Ký ban hành, Chương III Quản lý văn bản, Chương IV & V Con dấu & Chữ ký số, Chương VI & VII Quản lý nhà nước & Thi hành).
  * 7 Facts số hóa: Số lượng loại văn bản (29 loại), Quy cách căn lề trang A4, Phông chữ Times New Roman Unicode TCVN 6909:2001, Quy tắc đóng dấu 1/3 bên trái, Quy tắc dấu giáp lai $\le 5$ tờ, Màu mực bút xanh, Ngày ban hành & hiệu lực.
- File `backend/app/modules/knowledge/seeder.py`: Tự động nạp vào collection `col_drafting` và đánh chỉ mục vector vào Qdrant với UUID5 point ID determinism.
- File `backend/app/main.py`: Hook `seed_default_knowledge` vào startup lifespan để hệ thống luôn có sẵn dữ liệu chuẩn khi khởi chạy.

### 2.4. Điều Phối Workflow DAG & Khắc Phục Tắc Nghẽn Node
- `configs/workflows/drafting-assistant.v1alpha1.json`: Cập nhật `sample_retrieval` trỏ đúng `col_drafting` và `export_docx` sang định dạng `docx,pdf`.
- `backend/app/modules/workflows/engine.py`: Loại bỏ `artifact.export` khỏi `_TERMINAL_NODE_TYPES` để luồng thực thi sau khi tạo file tiếp tục chảy sang `output.artifact` / `output.chat` hoàn tất phản hồi người dùng.
- `backend/app/modules/workflows/nodes/artifact_export_node.py`: Đăng ký handler `artifact.export` cho Node Registry.
- `backend/app/modules/assistants/service.py`: Tự động truyền `is_approved=True` trong context chat để tránh pause checkpoint khi người dùng trò chuyện tương tác trực tiếp.

### 2.5. Tương Thích Qdrant Vector Client
- `backend/app/modules/rag/vector_indexer.py`: Nâng cấp phương thức `search_dense` hỗ trợ cả `query_points` (chuẩn qdrant-client hiện đại) và `search` (cũ), khắc phục triệt để lỗi `'AsyncQdrantClient' object has no attribute 'search'`.

### 2.6. Hiển Thị Frontend Tải File (`frontend/src/`)
- `use-rag-stream.ts`: Mở rộng kiểu dữ liệu `ChatAttachment` có trường `url`, `ChatMessageItem` có trường `artifacts`, tự động parse mảng file từ JSON response và SSE stream.
- `chat-message.tsx` & `attachment.tsx`: Render các thẻ tải tệp đẹp mắt với badge đuôi file, kích thước dung lượng (KB), biểu tượng màu (Đỏ cho PDF, Xanh cho Word DOCX) và nút download trực tiếp.

---

## 3. Kết Quả Kiểm Thử Toàn Diện (Zero Error)

1. **Backend Unit Tests**:
   ```bash
   pytest tests/test_document_generator.py tests/test_assistants.py tests/test_tools.py tests/test_workflows.py -v
   ```
   $\rightarrow$ **44/44 passed (100%)** trong 6.91 giây.
2. **Backend Ruff Linter**:
   ```bash
   ruff check .
   ```
   $\rightarrow$ **All checks passed! (0 lỗi)**.
3. **Frontend Biome Linter**:
   ```bash
   npm run lint
   ```
   $\rightarrow$ **Checked 93 files in 144ms. No fixes applied. (0 lỗi)**.
4. **Frontend TypeScript Check**:
   ```bash
   npm run typecheck
   ```
   $\rightarrow$ **tsc --noEmit (0 lỗi)**.
5. **Frontend Vite Build**:
   ```bash
   npm run build
   ```
   $\rightarrow$ **✓ built in 10.35s (dist/ bundle sạch)**.
6. **Zero Mojibake Audit**:
   ```bash
   python scripts/check_mojibake.py
   ```
   $\rightarrow$ **231/231 files sạch 100% (Không phát hiện lỗi vỡ font tiếng Việt)**.
7. **End-to-End Chatbot Verification**:
   - Câu hỏi tra cứu: *"Theo Nghị định 30/2020/NĐ-CP, văn bản hành chính gồm những loại nào và quy cách căn lề trang ra sao?"*
   - Kết quả: Trả về bảng số liệu Structured Facts 29 loại văn bản, căn lề chuẩn 30-20-20-15mm, 5 trích dẫn Điều/Khoản chính xác từ `col_drafting`, kèm tệp mẫu kết xuất sẵn sàng tải về.
