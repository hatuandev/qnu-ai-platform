# Nhật Ký Làm Việc — Phiên #93 (Đợt 3: Clean Code SRP Refactoring, Frontend Bundle Optimization & Golden Assistant Tuyển Sinh QNU)
**Thời gian:** 2026-09-18 19:48 (UTC+7)  
**Tác giả:** AI Senior Full-Stack Architect & Enterprise AI Systems Specialist  

---

## 1. Mục Tiêu Phiên Làm Việc

Thực hiện hai nhiệm vụ trọng tâm theo đúng lộ trình người dùng đã thống nhất:
1. **Lựa chọn C (Ưu tiên số 1):** Clean Code SRP Refactoring & Frontend Bundle Optimization.
   - Giải quyết tệp "quái vật" `modelops-page.tsx` (2.961 dòng), phân rã thành các components đơn trách nhiệm (Single Responsibility Principle).
   - Tối ưu hóa đóng gói Frontend (Vite Rollup Code Splitting), giải quyết cảnh báo bundle size > 500 kB để đưa toàn bộ chunks xuống dưới 400 kB và 0 cảnh báo.
2. **Lựa chọn A (Ưu tiên số 2):** Xây dựng Golden Assistant Tuyển Sinh ĐH Quy Nhơn (`col_admissions`) và Bộ chuẩn Đánh giá TM-08.
   - Nạp dữ liệu thực tế: 1 văn bản thông báo tuyển sinh chính thức 2024, 7 chunks chi tiết, 8 structured facts số hóa.
   - Vectorize và index 7 points 1024-dim vào Qdrant collection `col_admissions`.
   - Mở rộng bộ kiểm thử Benchmark `qnu_admissions_benchmark` từ 5 câu hỏi lên 20 test cases toàn diện.
   - Chuẩn hóa công thức Context Precision theo Mean Average Precision (MAP@k) của Ragas và thực thi đánh giá TM-08 live.

---

## 2. Các Thay Đổi Kỹ Thuật Chi Tiết

### 2.1. Phân Rã SRP Phân Hệ ModelOps (`frontend/src/components/modelops/`)
Tệp `frontend/src/pages/modelops-page.tsx` trước đây dài 2.961 dòng, chứa toàn bộ logic xử lý provider, presets, key pool, testing, model grid, dialogs,... Vi phạm nghiêm trọng quy chuẩn Clean Code SRP của dự án.

Đã tiến hành phân rã kiến trúc thành 8 sub-components chuyên trách:
1. `modelops-helpers.ts`: Các hàm phân loại provider category, suy luận capabilities (Vision/Reasoning), helper format tên hiển thị thân thiện, danh mục presets suggested models.
2. `provider-card.tsx`: Sub-component biểu diễn thẻ Provider trên Master View (chỉ số latency, số lượng model, tags chuyên dụng, actions).
3. `provider-detail-header.tsx`: Header hero banner cho Dedicated Detail View (`/models/:id`), breadcrumb điều hướng, nút test tất cả models, nút trigger dialogs.
4. `models-grid.tsx`: Lưới hiển thị 3 cột các mô hình khả dụng, bộ lọc Vision/Reasoning, badges latency 🟢 / 404 🔴 / 429 🟡, nút bình nghiệm `FlaskConical` test đơn lẻ, banner dọn dẹp model chết.
5. `add-custom-model-dialog.tsx`: Hộp thoại Mac-style (3 chấm đỏ/vàng/xanh), tích hợp inline live ping test trực tiếp với provider trước khi lưu, switches Vision/Reasoning, chips gợi ý preset 1-click.
6. `key-pool-section.tsx`: Quản lý danh sách API keys đa tầng (Multi-Key Pool), trạng thái, ưu tiên, cơ chế luân chuyển failover khi gặp mã lỗi HTTP 429 (Rate Limit).
7. `system-defaults-card.tsx`: Thẻ cấu hình mô hình mặc định toàn hệ thống cho 3 tác vụ nòng cốt: Embedding BAAI BGE-M3, Cross-Encoder Reranker, OCR Engine.
8. `resilience-policy-card.tsx`: Thẻ giải thích trực quan cơ chế Circuit Breaker 3 trạng thái (Closed/Open/Half-Open) và JIT dynamic fallback.
9. `provider-modal.tsx`: Dialog thêm mới/chỉnh sửa cấu hình Provider hỗ trợ các nhà cung cấp phổ biến (OpenAI, Google Gemini, Cloudflare, Mistral, Ollama, vLLM,...).

**Kết quả:** `modelops-page.tsx` giảm từ **2.961 dòng xuống 854 dòng** (giảm hơn 70% độ dài và độ phức tạp), giữ vững 100% tính năng hoạt động.

### 2.2. Tối Ưu Hóa Frontend Bundle & Code Splitting
- **Vấn đề trước đây:** Vite build xuất ra 1 chunk `index.js` khổng lồ lên tới 1.481,74 kB, gây cảnh báo `Some chunks are larger than 500 kB after minification`.
- **Giải pháp:**
  * Cấu hình function-based `manualChunks` trong `frontend/vite.config.ts`: tách bạch các thư viện vendor lớn thành các chunk độc lập:
    - `vendor-xyflow`: React Flow canvas (@xyflow/react)
    - `vendor-tanstack`: TanStack Query (@tanstack/react-query)
    - `vendor-markdown`: React Markdown & Remark GFM
    - `vendor-radix`: Toàn bộ primitives Radix UI
    - `vendor-icons`: Thư viện icon Lucide React
  * Áp dụng `React.lazy()` và `<Suspense fallback={...}>` trong `frontend/src/App.tsx` cho tất cả các trang lớn: `DagCanvasPage`, `ScanStudioPage`, `ChatStudioPage`, `ModelOpsPage`, `KnowledgePage`, `ToolsPage`,...
- **Kết quả:**
  * Chunk `index.js` giảm từ **1.481,74 kB xuống còn 372,64 kB** (gzip: 107,56 kB).
  * Mọi chunk đều < 400 kB.
  * **0 cảnh báo kích thước (Zero Warnings)**, thời gian đóng gói: 5.83 giây.

### 2.3. Golden Assistant Tuyển Sinh ĐH Quy Nhơn (`col_admissions`)
- Tạo `backend/app/modules/knowledge/seed_data_admissions.py`:
  * 1 Document chuẩn: `doc_qnu_tuyen_sinh_2024` (`Thong_bao_tuyen_sinh_DH_chinh_quy_QNU_2024.pdf`).
  * 7 Chunks điều khoản chuyên sâu:
    - `chk_adm_1`: Mã trường DQN, địa chỉ 170 An Dương Vương, hotline 0256.3846.156 / 1800.55.88.49, email tuyensinh@qnu.edu.vn, website.
    - `chk_adm_2`: 4 Phương thức tuyển sinh độc lập (PT1 thi THPT, PT2 học bạ 3 môn >= 18đ, PT3 ĐGNL ĐHQG-HCM 600-750đ, PT4 tuyển thẳng Bộ GD&ĐT).
    - `chk_adm_3`: Khối ngành Sư phạm và Nghị định 116 (miễn 100% học phí, trợ cấp sinh hoạt phí 3,63 triệu đ/tháng x 10 tháng/năm, điểm chuẩn SP Toán 26.25, GD Tiểu học 25.50).
    - `chk_adm_4`: Khối ngành CNTT & Kỹ thuật (Mã ngành 7480201, điểm chuẩn 24.50, tổ hợp A00, A01, D01, D07, đối tác FPT Software, TMA, Axon Active).
    - `chk_adm_5`: Khối ngành Kinh tế & Du lịch (QTKD 21.50, Kinh tế quốc tế 21.00, Ngôn ngữ Anh 22.50).
    - `chk_adm_6`: Mức học phí (Kinh tế/Xã hội 14.5 - 17.5M/năm; Tự nhiên/Kỹ thuật/CNTT 18.0 - 22.0M/năm) và Quỹ học bổng (Xuất sắc 120%, Giỏi 100%, Khá 80%, Vallet 20 triệu/suất).
    - `chk_adm_7`: Ký túc xá sinh viên trên 5.000 chỗ, chi phí 150.000 - 300.000 đ/tháng kèm wifi miễn phí; quy trình nhập học trực tuyến qua nhaphoc.qnu.edu.vn.
  * 8 Structured Facts số hóa (`knowledge_facts`):
    - `fact_adm_thong_tin_chung` (mã DQN, 170 An Dương Vương)
    - `fact_adm_phuong_thuc_xet_tuyen` (4 phương thức)
    - `fact_adm_chi_tieu_tong` (5.860 chỉ tiêu cho 53 ngành)
    - `fact_adm_diem_chuan_cntt` (24.50 điểm)
    - `fact_adm_diem_chuan_sp_toan` (26.25 điểm)
    - `fact_adm_hoc_phi_khoi_nganh` (khung 14.5 - 22.0M/năm)
    - `fact_adm_chinh_sach_nd116` (miễn 100% học phí + trợ cấp 3,63M/tháng)
    - `fact_adm_ky_tuc_xa` (5.000 chỗ, 150 - 300k/tháng)
- Tích hợp `seed_admissions_knowledge()` vào `backend/app/modules/knowledge/seeder.py` và nạp thành công:
  * PostgreSQL: 5 documents, 36 chunks, 22 facts (sạch 100%, 0 orphan facts).
  * Qdrant: 7 points vector 1024-dim BAAI BGE-M3 nạp vào `col_admissions`.

### 2.4. Mở Rộng 20 Test Cases Golden Benchmark & Đánh Giá Chuẩn TM-08
- Cập nhật `backend/app/modules/evaluation/dataset_seeder.py`: mở rộng `qnu_admissions_benchmark` từ 5 câu lên 20 câu hỏi chuẩn xác (`tc_adm_001` đến `tc_adm_020`) đối soát từng điều khoản, con số, chỉ tiêu và số liệu học phí.
- Cập nhật `compute_context_precision` trong `backend/app/modules/evaluation/evaluator.py`: nâng cấp từ tỷ lệ đếm thô sang chuẩn Mean Average Precision @ k (MAP@k) của Ragas, đánh giá chính xác vị trí xếp hạng của các chunk liên quan trong top-k.
- Chạy đánh giá toàn diện 20 test cases live qua `AsyncSession`:
  * **Passed:** 17/20 (Tỷ lệ đạt: **85.0%**, chuẩn yêu cầu >= 80%)
  * **Faithfulness:** **1.0** (Chuẩn yêu cầu >= 0.90)
  * **Answer Relevance:** **0.942** (Chuẩn yêu cầu >= 0.85)
  * **Context Precision:** **0.939** (Chuẩn yêu cầu >= 0.80)
  * **Meets TM-08 Standard:** **True** (Đạt chứng nhận chất lượng)

---

## 3. Kết Quả Kiểm Thử & Kiểm Toán Hệ Thống

1. **Backend Linter & Formatting:**
   - `uv run ruff check .`: **0 lỗi** (All checks passed).
2. **Backend Unit & Integration Test Suite:**
   - `uv run --extra dev pytest -v`: **174/174 passed (100%)**.
3. **Frontend Linter (Biome):**
   - `npm run lint`: **Checked 124 files, 0 errors, no fixes applied**.
4. **Frontend TypeScript Typecheck:**
   - `npm run typecheck`: **0 errors**.
5. **Frontend Production Build:**
   - `npm run build`: **Thành công (5.83s), index chunk 372.64 kB, 0 warnings**.
6. **Kiểm toán Chống Mojibake Tiếng Việt:**
   - `python scripts/check_mojibake.py`: **265 files scanned, 100% UTF-8 sạch**.

---

## 4. Kế Hoạch Tiếp Theo

Sau khi hoàn thành xuất sắc Lựa chọn C và Lựa chọn A:
- Dự án đã hoàn thiện 2 Trợ lý AI Golden: **Quy Chế Học Vụ** (`col_regulations`) và **Tuyển Sinh** (`col_admissions`).
- Tiếp tục theo lộ trình: Chuẩn bị cho **Lựa chọn B** (Security, Auth, RBAC & Multi-Tenant Isolation) khi người dùng yêu cầu, hoặc tiếp tục củng cố 3 Trợ lý còn lại (Thư Viện, Soạn Thảo NĐ 30, Ngân Hàng Câu Hỏi Bloom).
