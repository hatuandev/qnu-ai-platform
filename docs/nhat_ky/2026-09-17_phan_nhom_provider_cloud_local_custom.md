# NHẬT KÝ LÀM VIỆC — Phiên #62
# Ngày: 2026-09-17 | Tiêu đề: Phân Nhóm Provider Trực Quan: Cloud (Đám Mây), Local (Cục Bộ) & Custom (Tùy Chỉnh)

## 1. Bối Cảnh & Yêu Cầu
- **Yêu cầu từ người dùng**:
  "bạn có thể phân nhóm ra giúp tôi không, tôi muốn nhóm local, nhóm cloud, nhóm custom"
- **Mục tiêu**:
  Thay vì hiển thị toàn bộ Provider trên một lưới phẳng hỗn hợp, hệ thống cần phân nhóm rõ ràng theo 3 nhóm nghiệp vụ:
  1. **Nhóm Cloud (Đám Mây)**: Các nhà cung cấp mô hình AI và Edge GPU chạy trên đám mây (Cloudflare Workers AI, Mistral AI, OpenAI, Gemini,...).
  2. **Nhóm Local (Cục Bộ / On-Premise)**: Các mô hình AI chạy offline trên tài nguyên CPU/GPU máy chủ nội bộ ĐH Quy Nhơn (SentenceTransformers BGE-M3, Docling OCR, Ollama,...).
  3. **Nhóm Custom (Tùy Chỉnh / Tự Cấu Hình)**: Các cổng API tự cấu hình tương thích giao thức OpenAI API (vLLM, TGI, LocalAI, FastAPI tự phát triển,...).

## 2. Các Thay Đổi Kỹ Thuật Chi Tiết

1. **[`frontend/src/pages/modelops-page.tsx`](../../frontend/src/pages/modelops-page.tsx)**:
   - **Xác định loại nhóm (Taxonomy & Categorization)**:
     - Định nghĩa kiểu dữ liệu `ProviderCategory = "all" | "cloud" | "local" | "custom"`.
     - Triển khai hàm `getProviderCategory(prov)` tự động nhận diện danh mục dựa trên `type`, `code`, `id` và tên Provider:
       - `sentence_transformers`, `docling`, `ollama`, `local_vllm`, `local` → `"local"`.
       - `custom` → `"custom"`.
       - `cloudflare`, `mistral`, `openai`, `gemini`, `claude`, `deepseek`, `groq`, `openrouter`, `nvidia` → `"cloud"`.
   - **Bộ lọc Tabs chuyển nhóm nhanh (Category Filter Tabs)**:
     - Thêm thanh nút chuyển đổi dạng Tabs/Pills bo tròn:
       - `Tất Cả` (hiển thị tổng số Provider).
       - `Cloud (Đám Mây)` (icon `Cloud` kèm badge đếm số lượng).
       - `Local (Cục Bộ)` (icon `Cpu` kèm badge đếm số lượng).
       - `Custom (Tùy Chỉnh)` (icon `SlidersHorizontal` kèm badge đếm số lượng).
   - **Phân Khối Danh Mục Độc Lập (Grouped Sections)**:
     - Mỗi nhóm hiển thị phân khu riêng biệt với icon nhóm có màu nhận diện riêng (Sky cho Cloud, Emerald cho Local, Amber cho Custom), tiêu đề, badge đếm và mô tả định danh mục đích sử dụng.
     - Tích hợp nút thao tác nhanh trên từng tiêu đề: `+ Thêm Cloud`, `+ Thêm Local`, `+ Thêm Custom`.
     - Nhóm Custom khi chưa có Provider sẽ hiển thị thẻ hướng dẫn kết nối API OpenAI-compatible kèm nút bấm tạo mới nhanh.
   - **Cải tiến Hero Card Trang Chi Tiết**:
     - Bổ sung huy hiệu danh mục (Cloud / Local / Custom) ngay bên cạnh tên Provider và trạng thái hoạt động để người dùng luôn biết rõ ngữ cảnh đang xem.
   - **Dropdown Chọn Loại Provider trong Modal Tạo Mới**:
     - Bổ sung `Local SentenceTransformers (PyTorch)` và `Docling Local (IBM Research)` vào danh sách lựa chọn của Select menu.

## 3. Kết Quả Kiểm Thử & Đo Đạc
- **Frontend Code Quality**:
  - `npm run lint`: Biome check 83 files — 0 lỗi, tuân thủ 100% quy tắc Clean Code.
  - `npm run typecheck`: TypeScript `tsc --noEmit` — 0 lỗi type.
  - `npm run build`: Đóng gói bundle Vite production thành công trong 8.19s.
- **Backend**:
  - `uv run ruff check .`: 0 lỗi.
  - `pytest`: 34/34 ca kiểm thử RAG và Knowledge pass 100%.
