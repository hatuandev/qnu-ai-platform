# Nhật Ký Phiên Làm Việc #220 (2026-09-25 14:35)
## Chuẩn Hóa & Đồng Bộ Toàn Diện Tên 05 Mô-Đun, Trợ Lý AI & Kho Tri Thức Theo Thuyết Minh Đề Tài

---

### 1. Bối Cảnh & Mục Tiêu

Nhằm chuẩn hóa tên gọi toàn diện theo đúng thuyết minh đề tài nghiên cứu chính thức của Trường Đại học Quy Nhơn, người dùng đã chốt danh mục 05 mô-đun nghiệp vụ cùng cấu trúc đặt tên phân định rõ ràng giữa **Trợ lý AI** (tác nhân suy luận & giao tiếp) và **Kho tri thức** (cơ sở dữ liệu tài liệu RAG):

1. **Mô-đun trợ lý ảo tư vấn tuyển sinh** (`admissions`):
   - Trợ lý AI: **Trợ lý ảo Tư vấn Tuyển sinh**
   - Kho tri thức: **Kho Tri Thức Đề Án Tuyển Sinh** (`col_admissions`)
2. **Mô-đun trợ lý ảo tư vấn quy chế, quy định** (`regulations`):
   - Trợ lý AI: **Trợ lý ảo Tư vấn Quy chế, Quy định**
   - Kho tri thức: **Kho Tri Thức Quy Chế & Quy Định Đào Tạo** (`col_regulations`)
3. **Mô-đun trợ lý ảo hỗ trợ soạn thảo văn bản** (`drafting`):
   - Trợ lý AI: **Trợ lý ảo Hỗ trợ Soạn thảo Văn bản**
   - Kho tri thức: **Kho Tri Thức Thể Thức & Biểu Mẫu Văn Bản** (`col_drafting`)
4. **Mô-đun trợ lý ảo tra cứu, tư vấn khai thác tài nguyên thư viện** (`library`):
   - Trợ lý AI: **Trợ lý ảo Tra cứu & Khai thác Tài nguyên Thư viện**
   - Kho tri thức: **Kho Tri Thức Tài Nguyên Thư Viện & Học Liệu Số** (`col_library`)
5. **Mô-đun trợ lý ảo hỗ trợ tạo câu hỏi, ngân hàng câu hỏi theo chuẩn đầu ra** (`question_bank`):
   - Trợ lý AI: **Trợ lý ảo Hỗ trợ Tạo Câu hỏi & Ngân hàng Đề thi theo Chuẩn Đầu ra**
   - Kho tri thức: **Kho Tri Thức Ngân Hàng Câu Hỏi & Chuẩn Đầu Ra** (`col_question_bank`)

---

### 2. Các Tác Vụ Đã Thực Hiện

1. **Tài Liệu Tổng Quan Dự Án (`README.md`)**:
   - Cập nhật phần giới thiệu tổng thể, bổ sung danh sách 05 mô-đun chính thức kèm mã định danh, tên Trợ lý AI và tên Kho tri thức tương ứng.
2. **Backend Seeders & Services**:
   - `backend/app/modules/assistants/seeder.py`: Cập nhật trường `name`, `system_prompt` và `persona` của 5 trợ lý AI chuẩn.
   - `backend/app/modules/knowledge/seeder.py`: Cập nhật tên của các bản ghi `KnowledgeCollection` tương ứng.
   - `backend/app/modules/knowledge/services/collection_service.py`: Cập nhật danh mục `seed_data` khi khởi tạo kho tri thức cho workspace mới.
3. **Cấu Hình Quy Trình DAG (`configs/workflows/*.json`)**:
   - Cập nhật trường `display_name` trong 5 tệp workflow template: `admissions-assistant`, `regulations-assistant`, `drafting-assistant`, `library-assistant`, `question-bank-assistant`.
4. **Giao Diện Người Dùng (`frontend2`)**:
   - `frontend2/src/features/dashboard/dashboard-page.tsx`: Cập nhật danh sách trợ lý mặc định (`defaultAssistants`).
   - `frontend2/src/components/evaluation/run-benchmark-dialog.tsx`: Cập nhật danh sách tùy chọn trợ lý fallback trong hộp thoại đánh giá benchmark.
5. **Cập Nhật CSDL Trực Tiếp (Live Database Synchronization)**:
   - Chạy script cập nhật bản ghi trực tiếp trong bảng `assistants` và `knowledge_collections` trên PostgreSQL 16 qua `AsyncSessionFactory`.
   - Cả 5 trợ lý và 5 kho tri thức trên giao diện thực tế cập nhật ngay lập tức mà không cần xóa database hay reset dữ liệu.

---

### 3. Kết Quả Kiểm Thử (Fast-Path Verification)

- **Backend Linting**: `uv run ruff check` đạt **0 lỗi, 100% clean**.
- **Frontend2 Formatting & Build**:
  - `npx @biomejs/biome format --write`: Đạt chuẩn format.
  - `npm run build`: Vite build và TypeScript typecheck hoàn tất thành công (`exit code 0`).
- **PostgreSQL Database**:
  - `ast_admissions`: Trợ lý ảo Tư vấn Tuyển sinh
  - `ast_regulations`: Trợ lý ảo Tư vấn Quy chế, Quy định
  - `ast_drafting`: Trợ lý ảo Hỗ trợ Soạn thảo Văn bản
  - `ast_library`: Trợ lý ảo Tra cứu & Khai thác Tài nguyên Thư viện
  - `ast_question_bank`: Trợ lý ảo Hỗ trợ Tạo Câu hỏi & Ngân hàng Đề thi theo Chuẩn Đầu ra
  - Toàn bộ 5 kho tri thức tương ứng đã đồng bộ 100%.
