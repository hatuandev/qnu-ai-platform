# Nhật Ký Làm Việc — Phiên #99
# Ngày: 2026-09-18 | Mục Tiêu: Rà Soát Toàn Diện & Nâng Cấp Đồng Bộ 5 Trợ Lý AI Cốt Lõi QNU

---

## 1. Thời Gian & Bối Cảnh
- **Thời gian**: 2026-09-18 22:05 (UTC+7)
- **Bối cảnh**: Sau khi phân tích định hướng nền tảng tại [`docs/gop_y_dinh_huong_chuc_nang_trong_tam_qnu_ai_platform_2026-09-18.md`](../gop_y_dinh_huong_chuc_nang_trong_tam_qnu_ai_platform_2026-09-18.md), người dùng chọn Hướng 2: Rà soát 1 lượt cả 5 trợ lý cốt lõi (Tuyển sinh, Quy chế, Thư viện, Soạn thảo NĐ 30, Ngân hàng đề thi Bloom) nhằm đảm bảo 5 trợ lý đạt chuẩn nghiệp vụ thực tế phục vụ cán bộ, giảng viên và sinh viên ĐH Quy Nhơn.

---

## 2. Chi Tiết Thay Đổi Kỹ Thuật (Key Changes)

### 2.1. Khớp Nối Tool Mappings & Cập Nhật Câu Hỏi Mẫu Sát Thực Tế (Phase 1)
- **Tệp chỉnh sửa**: [`backend/app/modules/assistants/seeder.py`](../../backend/app/modules/assistants/seeder.py)
  - Khớp nối `enabled_tools` cho `ast_admissions`: Sửa từ `admissions.fact_lookup` thành `lookup_admission_score` (khớp hoàn toàn với registry).
  - Khớp nối `enabled_tools` cho `ast_question_bank`: Sửa từ `assessment.xlsx_export` thành `export_exam_matrix`.
  - Cập nhật 4 câu hỏi gợi ý (`sample_questions`) trực quan, thực tế cho cả 5 trợ lý để người dùng bấm thử nghiệm ngay trên Chat Studio.

### 2.2. Làm Giàu Tri Thức & Structured Facts Cho 5 Trợ Lý (Phase 2)
- **Tệp chỉnh sửa**: [`backend/app/modules/knowledge/seed_data_admissions.py`](../../backend/app/modules/knowledge/seed_data_admissions.py)
  - Bổ sung Chunk `chk_adm_8` (Phần VIII): Bảng tổng hợp điểm chuẩn 3 năm liên tiếp (2022, 2023, 2024) của các ngành Sư phạm Toán, Giáo dục Tiểu học, Sư phạm Văn, Sư phạm Tiếng Anh, CNTT, Kỹ thuật phần mềm, Quản trị kinh doanh.
  - Bổ sung `fact_adm_diem_chuan_3_nam` lưu trữ có cấu trúc xu hướng điểm chuẩn qua các năm.
- **Tệp chỉnh sửa**: [`backend/app/modules/knowledge/seed_data_library.py`](../../backend/app/modules/knowledge/seed_data_library.py)
  - Bổ sung trong `chk_lib_6`: Quy định kiểm tra đạo văn Turnitin rõ ràng (tổng thể < 20%, nguồn đơn lẻ < 5%), quy trình nộp lưu chiểu bản mềm luận văn tốt nghiệp định dạng PDF lên cổng https://lib.qnu.edu.vn.
  - Cập nhật `fact_lib_kiem_tra_dao_van` có các thuộc tính metadata `max_total_similarity: 0.20`, `max_single_source_similarity: 0.05`.

### 2.3. Trải Nghiệm Tải File Trực Tiếp Trong Khung Chat (Phase 3)
- **Tệp chỉnh sửa**: [`frontend/src/components/ai/chat-message.tsx`](../../frontend/src/components/ai/chat-message.tsx)
  - Thêm icon `FileSpreadsheet` từ `lucide-react` cho các tệp Excel (`.xlsx`, `.xls`) kết xuất từ Trợ lý Ngân hàng đề thi Bloom với màu xanh ngọc (`text-emerald-600`).
  - Tiêu đề khối tải tệp linh hoạt theo ngữ cảnh: "Ma trận đề thi kết xuất" (nếu có tệp Excel) hoặc "Tài liệu kết xuất" (nếu có tệp Word/PDF).

### 2.4. Mở Rộng Bộ Kiểm Định Vàng TM-08 (Phase 4)
- **Tệp chỉnh sửa**: [`backend/app/modules/evaluation/dataset_seeder.py`](../../backend/app/modules/evaluation/dataset_seeder.py)
  - Mở rộng `qnu_regulations_benchmark` từ 20 lên **50 test cases** vàng (`tc_reg_001` - `tc_reg_050`) bao quát mọi quy định: thang điểm chữ quy đổi hệ 4, các mốc cảnh báo học vụ năm 1-4, điều kiện buộc thôi học, hạn ngạch tín chỉ kỳ chính/kỳ hè, chuẩn ngoại ngữ VSTEP B1/C1, TOEIC/IELTS, chuẩn tin học TT 03, điều kiện tốt nghiệp và hạ bậc bằng tốt nghiệp.
  - Nâng tổng số test cases kiểm định TM-08 của cả 5 trợ lý lên **130 câu hỏi vàng**.

---

## 3. Kết Quả Kiểm Thử (Verification)
- **Backend Ruff**: `uv run ruff check .` $\rightarrow$ All checks passed! (0 lỗi).
- **Backend Pytest**: `uv run --extra dev pytest -v` $\rightarrow$ **182/182 passed (100%)** trong 62.02s.
- **Frontend Biome**: `npm run lint` $\rightarrow$ Checked 124 files in 161ms (0 lỗi).
- **Frontend Typecheck**: `npm run typecheck` $\rightarrow$ 0 lỗi (`tsc --noEmit`).
- **Frontend Vite Build**: `npm run build` $\rightarrow$ Đóng gói thành công trong 13.12s, 0 cảnh báo.
- **Zero Mojibake**: `python scripts/check_mojibake.py` $\rightarrow$ Quét 271 tệp, 100% UTF-8 sạch.
