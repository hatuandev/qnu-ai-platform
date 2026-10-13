# Phiên 388 — Chẩn đoán batch 20 tài liệu tuyển sinh

## Phạm vi

Kiểm tra read-only batch `imp_batch_dc04584eee1f` sau khi người dùng reset DB. Không sửa runtime, duyệt, retry, reparse, xuất bản, reset hoặc restart worker.

## Bằng chứng

- PostgreSQL transaction READ ONLY: 20 items, 11 succeeded, 8 review_required, 1 failed; không item đang xử lý.
- Failed: BC Kết quả khảo sát Tư vấn tuyển sinh 2022.pdf, EMPTY_OCR_PAGE trang 8. PDF có 8 trang; render trang cuối gần trắng với nhiễu lẻ. Raster classifier: background 255, foreground 221, largest component 33; vượt giới hạn speck hiện tại (128/16), nên từ chối blank. Không có native text. Chưa kiểm định đủ 7 trang OCR còn lại.
- Cac nganh Tuyen sinh 2025_moi.pdf: native text 122 ký tự, 173 image placements, tổng image coverage 1.9757 (có chồng lấp). Ảnh render có bảng 52 ngành nhưng extraction dùng native, report 116 ký tự. Router yêu cầu image coverage >0.5 VÀ native chars <80 nên lọt OCR. Cần coverage không chồng lấp và kiểm định độ đầy đủ, không chỉ hạ/ngẩng ngưỡng chars.
- TABLES_NOT_MATERIALIZED: tư vấn tuyển sinh 26.docx; Quy chế tuyển sinh đại học 2026 - 363.pdf; NQ57.2024_ Phương hướng tuyển sinh 2025.pdf; Muc hoc phi 2024.pdf; Cac nganh Tuyen sinh 2025_moi.pdf. Parser/regions báo bảng nhưng structured GFM không có bảng; không có HTML table trong canonical MD. Chưa kết luận mọi vùng table đều là bảng dữ liệu thật.
- TB lịch xét tuyển ĐH.pdf: conflict tại table_1 row 4. Identity lấy mốc thời gian, hai công việc có cùng hạn 10/7/2026 bị coi mâu thuẫn vì khóa thiếu ngữ cảnh hàng.
- TB điểm sàn 26.pdf: table_2 headers chứa nguyên dòng dữ liệu ngành 16 (7140249, điểm 20...), cho thấy bảng tiếp nối bị coi dòng dữ liệu là header; cảnh báo conflict downstream không đáng tin trước khi sửa cấu trúc.
- Phuong huong tuyen sinh 2024_DHQN_final.docx: table_8/9 thiếu header cột 5/6. Table_8 có nhóm năm 2021/2022/2023 trong dòng đầu với cột phân nhóm “Trình độ tiến sĩ”; thuật toán header chỉ nhận dòng đầu trống nên bỏ lỡ.
- 90% = (11*100 + 8*85 + 1*20)/20. Đây là trung bình mốc pipeline, không phải worker còn chạy. UI cần tách tiến độ xử lý và trạng thái duyệt/kết quả.
- Thư mục bản gốc có 21 file; batch chỉ 20, không gồm Cẩm Nang Tuyển Sinh Đại Học Năm 2025 (1).pdf.

## Đề xuất trước triển khai

1. Blank-page morphology đa tỉ lệ, xem phân bố và hình dạng nhiễu; không bỏ qua trang OCR rỗng có nội dung thật.
2. Native/OCR routing dựa độ phủ văn bản hữu ích và ảnh hợp nhất; rescue trang có lớp chữ rất ít nhưng nội dung ảnh lớn.
3. Bảng canonical chung giữ spans/header tree/page continuation; không ép mọi vùng bảng thành GFM hoặc facts.
4. Fact identity/constraint đầy đủ ngữ cảnh hàng, năm, phương thức; loại false conflict nhưng giữ conflict thật.
5. UI tiến độ xử lý độc lập approval; lý do cảnh báo dễ hiểu, không duyệt hàng loạt khi thiếu dữ liệu.

## Kiểm tra và tệp thay đổi

DB SELECT read-only, trích xuất PyMuPDF, render/visual inspection 2 trang, đọc code routing/blank/artifact/header/progress. Không chạy Ruff/Pytest/Vite vì không đổi code ứng dụng; chưa retry OCR hoặc tải thử production. Tạo 2 PNG chẩn đoán trong backend/storage, cập nhật nhật ký/index/memory/work log.
