# Nhật Ký Phiên Làm Việc #235 — Thu Thập & Tổ Chức 17 Tệp Tài Liệu Tuyển Sinh QNU Vào Thư Mục docs/tai_lieu

- **Thời gian**: 2026-09-30 23:35 (UTC+7)
- **Tác giả**: AI Senior Full-Stack Architect & Enterprise AI Systems Specialist
- **Trạng thái**: Hoàn thành xuất sắc, đã tải thành công 17/17 tệp (9.34 MB), lập mục lục README.md chi tiết

---

## 1. Yêu Cầu & Bối Cảnh Thực Tế

1. **Thu thập tài liệu tuyển sinh chính thức của Trường Đại học Quy Nhơn**:
   - Người dùng yêu cầu tạo thư mục tài liệu trong `docs/` (`docs/tai_lieu/`) và tự động tìm kiếm, tải toàn bộ tệp PDF từ 3 liên kết tuyển sinh chính thức:
     - Đại học chính quy: `https://tuyensinh.qnu.edu.vn/vi/tuyen-sinh-dai-hoc-chinh-quy-2027`
     - Sau đại học: `https://tuyensinh.qnu.edu.vn/vi/tuyen-sinh-sau-dai-hoc-2028`
     - Vừa làm vừa học / Đào tạo từ xa: `https://tuyensinh.qnu.edu.vn/vi/tuyen-sinh-vua-lam-vua-hoc-2029`
2. **Quy định đẩy mã nguồn (Git Push Policy)**:
   - Người dùng yêu cầu AI Agent **không tự ý chạy `git push`** sau mỗi lần hoàn thành tác vụ / vibe coding. Việc push mã nguồn lên các remote Git (Gitea / GitHub) sẽ do người dùng chủ động thực hiện.
3. **Quy chuẩn Nhật ký & Memory bắt buộc**:
   - Mọi phiên làm việc phải được cập nhật ngay lập tức vào:
     - `docs/nhat_ky/`: Tệp nhật ký chi tiết của phiên.
     - `docs/WORK_LOG.md`: Bảng mục lục tổng hợp tiến trình.
     - `docs/memory/PROJECT_CONTEXT.md`: Snapshot trạng thái hệ thống.

---

## 2. Các Thành Phần Kỹ Thuật Đã Triển Khai

### 2.1 Xây Dựng Pipeline Thu Thập & Chuẩn Hóa URL
- **Bộ Quét Liên Kết & Bài Viết (`scan_all_admissions.py`)**:
  - Tự động bóc tách các bài viết thông báo con và tìm kiếm các tệp đính kèm (`.pdf`, `.docx`, `.xlsx`, liên kết Google Drive).
  - Khám phá 10 bài viết ĐHCQ, 6 bài viết Sau đại học và 6 bài viết Vừa làm vừa học.
- **Xử Lý Lỗi Double Percent-Encoding (`normalize_url`)**:
  - Phát hiện và giải quyết triệt để lỗi HTTP 404 khi tải các URL tiếng Việt đã được encode sẵn từ trước (`%20`, `%E1%...`).
  - Hàm `normalize_url` thực hiện `unquote` trước khi chia tách và mã hóa đường dẫn một cách chuẩn mực, giúp 100% các request tải về trả về HTTP 200.
- **Tải Tệp Google Drive**:
  - Bóc tách file ID từ liên kết chia sẻ Google Drive (TB123 - Quy đổi điểm) và tải trực tiếp qua endpoint export download của Google Drive API.

### 2.2 Cấu Trúc Thư Mục Lưu Trữ
- Khởi tạo thư mục chuẩn: `docs/tai_lieu/`:
  - **`dai_hoc_chinh_quy/`** (6 tệp):
    1. `TB123_Quy_doi_tuong_duong_diem_xet_tuyen_2026.pdf` (348 KB)
    2. `Thong_bao_diem_chuan_DGNL_va_hoc_ba_DHCQ_2026.pdf` (635 KB)
    3. `1897_Bao_cao_thuc_hien_chi_tieu_tuyen_sinh_2025.pdf` (349 KB)
    4. `1897_BC02_Co_so_phap_ly_xac_dinh_chi_tieu_2026.pdf` (1.45 MB)
    5. `1897_BC03_Dieu_kien_xac_dinh_chi_tieu_tuyen_sinh_2026.pdf` (1.52 MB)
    6. `1897_Dang_ky_chi_tieu_tuyen_sinh_nam_2026.pdf` (374 KB)
  - **`sau_dai_hoc/`** (8 tệp):
    7. `Phu_luc_1_Tuyen_sinh_thac_si_2026_Quy_doi_chung_chi_ngoai_ngu.pdf` (203 KB)
    8. `Phu_luc_2_Tuyen_sinh_thac_si_2026_Don_vi_cap_chung_chi_tieng_Viet.pdf` (185 KB)
    9. `Phu_luc_3_Tuyen_sinh_thac_si_2026_Nganh_phu_hop_va_bo_sung_kien_thuc.pdf` (293 KB)
    10. `Phu_luc_1_Tuyen_sinh_tien_si_2026_Huong_nghien_cuu_va_nguoi_huong_dan.pdf` (322 KB)
    11. `Phu_luc_2_Tuyen_sinh_tien_si_2026_Danh_muc_nganh_phu_hop.pdf` (671 KB)
    12. `Phu_luc_3_Tuyen_sinh_tien_si_2026_Chung_chi_ngoai_ngu.pdf` (277 KB)
    13. `Phu_luc_4_Tuyen_sinh_tien_si_2026_Don_vi_cap_chung_chi_tieng_Viet.pdf` (319 KB)
    14. `Phu_luc_5_Tuyen_sinh_tien_si_2026_Ho_so_du_tuyen.docx` (80 KB)
  - **`vua_lam_vua_hoc/`** (3 tệp):
    15. `QD2139_Muc_thu_hoc_phi_dao_tao_dai_hoc_tu_xa_dot_1.pdf` (815 KB)
    16. `TB2302_Thong_bao_tuyen_sinh_dao_tao_tu_xa_trinh_do_dai_hoc.pdf` (880 KB)
    17. `TB2618_Tuyen_sinh_dai_hoc_vua_lam_vua_hoc_GDTX_Gia_Lai.pdf` (772 KB)
- **Tệp Mục Lục [`docs/tai_lieu/README.md`](file:///d:/DuAnPhanMem/qnu-ai-platform/docs/tai_lieu/README.md)**:
  - Bảng tổng hợp chi tiết phân loại, tên gọi tiếng Việt, dung lượng và liên kết tải về cho từng tệp.

---

## 3. Kết Quả Kiểm Tra (Verification)
- Tổng cộng 17 tệp (9.34 MB) đã tải hoàn chỉnh, kiểm tra không bị hỏng tệp.
- Kiểm thử đọc nội dung bằng `PyMuPDF` xác nhận các trang chứa đầy đủ bảng biểu chỉ tiêu, điểm chuẩn và quy chế.
- Toàn bộ tài liệu sẵn sàng để nạp vào Kho Tri Thức (`knowledge_collections`) phục vụ RAG.
