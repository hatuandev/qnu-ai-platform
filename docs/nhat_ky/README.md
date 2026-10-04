# THƯ MỤC NHẬT KÝ LÀM VIỆC (ENGINEERING WORK LOGS DIRECTORY)
## Dự Án: QNU.AI Platform — Trường Đại Học Quy Nhơn

> **Quy định bắt buộc**: Mỗi khi bắt đầu và kết thúc một phiên làm việc ("Vibe Coding") — bao gồm phát triển tính năng, tái cấu trúc (refactor), sửa lỗi, cấu hình hạ tầng hay kiểm thử — **Kỹ sư / AI Agent BẮT BUỘC phải tạo hoặc cập nhật nhật ký làm việc vào thư mục này**.

---

## 🗂️ Danh Mục Nhật Ký Làm Việc Theo Phiên

| **2026-10-04** | [`2026-10-04_phien_255_nang_cap_giao_dien_chat_chuan_chatgpt_gemini_va_lich_su_hoi_thoai.md`](./2026-10-04_phien_255_nang_cap_giao_dien_chat_chuan_chatgpt_gemini_va_lich_su_hoi_thoai.md) | Nâng cấp toàn diện giao diện Chat chuẩn ChatGPT/Gemini, Sidebar Lịch sử hội thoại & Floating Input Dock | 0 lỗi Biome, Vite build 0 lỗi (3.75s), giao diện chat chuẩn hiện đại, đa phiên hội thoại |
| **2026-10-04** | [`2026-10-04_phien_254_toi_uu_responsive_grid_cards_cho_man_hinh_laptop_va_desktop.md`](./2026-10-04_phien_254_toi_uu_responsive_grid_cards_cho_man_hinh_laptop_va_desktop.md) | Tối ưu Responsive Grid Cards cho Laptop 14" (3 cột) và Desktop 24"+ (4 cột) trên Trợ lý AI, Kho tri thức, ModelOps | Vite build 0 lỗi (5.84s), giao diện card thông thoáng, không còn bị che khuất nội dung |
| **2026-10-04** | [`2026-10-04_phien_253_hoan_thien_toan_dien_sso_bearer_injection_va_fine_grained_rbac.md`](./2026-10-04_phien_253_hoan_thien_toan_dien_sso_bearer_injection_va_fine_grained_rbac.md) | Hoàn thiện toàn diện tích hợp QNU Single Sign-On (OIDC), tự động inject Bearer Token & Enforce Fine-Grained RBAC | Backend 15/15 tests passed, 0 Ruff errors, 0 Biome errors, Vite build 0 lỗi (6.15s) |
| **2026-10-04** | [`2026-10-04_phien_252_tich_hop_xac_thuc_tap_trung_qnu_sso_openiddict_va_phan_quyen_rbac.md`](./2026-10-04_phien_252_tich_hop_xac_thuc_tap_trung_qnu_sso_openiddict_va_phan_quyen_rbac.md) | Tích hợp xác thực tập trung QNU Single Sign-On (OpenIddict) & Phân quyền RBAC 25 quyền hạn fine-grained | Backend 12/12 test passed, 0 Biome lint errors, Vite build 0 lỗi, Dual-Auth (SSO + Dev Gate) |
| **2026-10-04** | [`2026-10-04_phien_251_trien_khai_cong_chat_cong_khai_va_kenh_widget_prod.md`](./2026-10-04_phien_251_trien_khai_cong_chat_cong_khai_va_kenh_widget_prod.md) | Triển khai Kế hoạch Production: Cổng Chat Công Khai (`/chat`, `/chat/:slug`) và Kênh Web Chat Widget (`/channels`) | Vite build 0 lỗi (4.14s), Cổng chat độc lập cho thí sinh/sinh viên & Live Preview Widget 1:1 hoàn tất |
| **2026-10-04** | [`2026-10-04_phien_250_don_dep_menu_sidebar_frontend_va_ra_soat_chuc_nang.md`](./2026-10-04_phien_250_don_dep_menu_sidebar_frontend_va_ra_soat_chuc_nang.md) | Dọn dẹp menu Sidebar Frontend, loại bỏ các mục liên kết chưa có Route (404), tinh gọn 3 nhóm chức năng cốt lõi | Vite build 0 lỗi (10.82s), loại bỏ triệt để liên kết 404, Sidebar sạch 100% |
| **2026-10-03** | [`2026-10-03_phien_249_gan_cung_loai_tac_vu_combo_theo_4_tab_modelops.md`](./2026-10-03_phien_249_gan_cung_loai_tac_vu_combo_theo_4_tab_modelops.md) | Gán cứng loại tác vụ Combo theo 4 Tab ModelOps (Vision OCR, Vector Embedding, Reranker, LLM Chat), xóa bỏ hoàn toàn nút hoán đổi gây hiểu lầm trong Modal | Tái cấu trúc UX/UI Combos, header button thông minh theo Tab, gán cứng cố định kênh tác vụ, cảnh báo model không có vision |
| **2026-10-03** | [`2026-10-03_phien_248_chuan_hoa_adapter_openai_vision_va_toi_uu_ocr_combo_multimodal.md`](./2026-10-03_phien_248_chuan_hoa_adapter_openai_vision_va_toi_uu_ocr_combo_multimodal.md) | Chuẩn hóa OpenAIVisionOCRAdapter, cleaner chuyển đổi HTML layout table sang Markdown, stitch bảng tiếp nối qua trang, dọn dẹp qwen_adapter.py & tối ưu OCR Combo | 24/24 unit test OCR passed (100%), 0 lỗi Ruff, Protocol-Based Adapters hoàn tất |
| **2026-10-03** | [`2026-10-03_phien_247_khu_bang_gia_footnote_demotion_va_nang_cap_ocr_combo_gemini_3.md`](./2026-10-03_phien_247_khu_bang_gia_footnote_demotion_va_nang_cap_ocr_combo_gemini_3.md) | Khử bảng giả (Footnote Demotion), gộp cột lệch lưới & nâng cấp OCR Combo Gemini 3.x Flash-Lite | Multi-file upload frontend, 3 tệp scan pure image đạt ready, giải quyết triệt để 409 Conflict |
| **2026-10-02** | [`2026-10-02_phien_246_khoi_phuc_docling_office_parser.md`](./2026-10-02_phien_246_khoi_phuc_docling_office_parser.md) | Khôi phục Docling Office Parser (DOCX, XLSX, PPTX), giữ OCR cloud và native fallback | Sửa lỗi thứ tự check extension & table markdown, 5/5 test parser passed, compileall đạt |
| **2026-10-02** | [`2026-10-02_phien_245_loai_bo_model_local.md`](./2026-10-02_phien_245_loai_bo_model_local.md) | Loại bỏ toàn bộ runtime AI local, chuyển ModelOps sang provider API key | Xóa adapter/dependency/cache local, migration DB thành công, build hai frontend và 69 test trọng điểm đạt |
| **2026-10-02** | [`2026-10-02_phien_244_kiem_thu_chatbot_tuyen_sinh_20_cau.md`](./2026-10-02_phien_244_kiem_thu_chatbot_tuyen_sinh_20_cau.md) | Kiểm thử assistant `admissions` bằng 20 câu đối chiếu 7 PDF | 14 đạt, 3 một phần, 3 không đạt; phát hiện cache phản hồi suy giảm và sai routing số liệu |
| **2026-10-02** | [`2026-10-02_phien_243_sua_trang_thai_khoa_api_disabled.md`](./2026-10-02_phien_243_sua_trang_thai_khoa_api_disabled.md) | Chuẩn hóa trạng thái khóa API legacy và sửa lỗi HTTP 500 | Endpoint Gemini keys HTTP 200, migration + DB constraint, 23 test trọng điểm đạt |
| **2026-09-15** | [`2026-09-15_hoan_thanh_8_giai_doan_backend.md`](./2026-09-15_hoan_thanh_8_giai_doan_backend.md) | Xây dựng toàn diện 8 Giai đoạn Backend theo chuẩn Enterprise Modular Monolith | 8/8 Giai đoạn hoàn thành, 68/68 Pytest Passed |
| **2026-09-15** | [`2026-09-15_kiem_thu_doc_lap_37_chuc_nang.md`](./2026-09-15_kiem_thu_doc_lap_37_chuc_nang.md) | Chạy kiểm thử chức năng độc lập 8 phân hệ qua `scripts/verify_all_modules.py` | 37/37 Chức năng Đạt chuẩn (100% Passed) |
| **2026-09-15** | [`2026-09-15_chuan_hoa_docker_minio.md`](./2026-09-15_chuan_hoa_docker_minio.md) | Chuẩn hóa Docker Compose duy nhất, Dockerfile Backend & MinIO Object Storage | Docker compose valid 100%, MinIO-First |

---

## 📝 Mẫu Tiêu Chuẩn Ghi Nhật Ký Cho Phiên Làm Việc Mới (Template)

Mỗi khi tạo tệp nhật ký mới (đặt tên theo định dạng `YYYY-MM-DD_ten_tinh_nang.md`), hãy sử dụng mẫu cấu trúc sau:

```markdown
# NHẬT KÝ LÀM VIỆC: [TIÊU ĐỀ PHIÊN LÀM VIỆC]
- **Thời gian**: [YYYY-MM-DD HH:MM]
- **Kỹ sư / Agent**: AI Senior Backend Architect & Enterprise Specialist
- **Mục tiêu phiên (Goals)**:
  - [Mục tiêu 1]
  - [Mục tiêu 2]

## 1. Các Thay Đổi Mã Nguồn & Kiến Trúc (Key Changes)
- `duong/dan/tep_1`: [Mô tả chi tiết lý do và nội dung thay đổi]
- `duong/dan/tep_2`: [Mô tả chi tiết lý do và nội dung thay đổi]

## 2. Tuân Thủ Chuẩn MinIO Object Storage
- [Xác nhận luồng lưu trữ file upload gốc và artifact đầu ra qua MinIO S3]

## 3. Kết Quả Kiểm Thử & Xác Minh (Verification)
- Lệnh kiểm tra Linter: `uv run ruff check .` -> [Kết quả]
- Lệnh kiểm tra Test Suite: `uv run pytest -v` -> [Kết quả]
- Kiểm thử chức năng: [Mô tả kịch bản test thực tế]

## 4. Trạng Thái & Công Việc Tiếp Theo (Next Steps)
- Trạng thái phiên: [HOÀN THÀNH / ĐANG TIẾN HÀNH]
- Đề xuất việc cần làm tiếp theo: [Nội dung]
```
