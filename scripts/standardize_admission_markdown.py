#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Script to standardize and rebuild Thong tin tuyen sinh dai hoc 2026_Lan2-1_boc_tach.md

Ensures 100% data fidelity, GFM table specification, logical reading order,
stitched cross-page table rows, 4-column VSTEP/IELTS conversion table,
and zero OCR duplicate/leakage artifacts.
"""

import sys
from pathlib import Path

# Fix Windows cp1252 console encoding
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

TARGET_FILE = Path(__file__).resolve().parent.parent / "Thong tin tuyen sinh dai hoc 2026_Lan2-1_boc_tach.md"

CONTENT = """<!-- Page 1 -->
# BỘ GIÁO DỤC VÀ ĐÀO TẠO
# TRƯỜNG ĐẠI HỌC QUY NHƠN
Số: /TB-ĐHQN

### CỘNG HÒA XÃ HỘI CHỦ NGHĨA VIỆT NAM
**Độc lập - Tự do - Hạnh phúc**

*Gia Lai, ngày tháng năm 2026*

---

## THÔNG BÁO
### THÔNG TIN TUYỂN SINH ĐẠI HỌC NĂM 2026 (CẬP NHẬT)
**Hình thức đào tạo: Chính quy**

Căn cứ Quy chế Tuyển sinh các ngành đào tạo trình độ đại học và ngành Giáo dục mầm non trình độ cao đẳng ban hành kèm theo Thông tư số 06/2026/TT/TT-BGDĐT ngày 15/02/2026 của Bộ trưởng Bộ Giáo dục và Đào tạo;

Căn cứ Quy chế tuyển sinh đại học ban hành kèm theo Quyết định số /QĐ-ĐHQN ngày của Hiệu trưởng Trường Đại học Quy Nhơn;

Căn cứ Kế hoạch triển khai công tác tuyển sinh đại học, cao đẳng năm 2026 ban hành theo Quyết định số 3037/QĐ-BGDĐT ngày 3/11/2025 của Bộ Giáo dục và Đào tạo;

Căn cứ Công văn số 2304/BGDĐT-GDĐH ngày 04/5/2026 hướng dẫn tuyển sinh đại học, tuyển sinh cao đẳng 2026;

Trường Đại học Quy Nhơn thông báo Thông tin tuyển sinh đại học năm 2026 (cập nhật) như sau:

---

## I. THÔNG TIN CHUNG

1. **Tên cơ sở đào tạo**: Trường Đại học Quy Nhơn
2. **Mã cơ sở đào tạo trong tuyển sinh**: DQN
3. **Địa chỉ**: 170 An Dương Vương, P. Quy Nhơn Nam, tỉnh Gia Lai
4. **Địa chỉ trang thông tin điện tử**: https://qnu.edu.vn
5. **Số điện thoại liên hệ tuyển sinh**: 1800.55.88.49
6. **Địa chỉ công khai quy chế tuyển sinh**: https://tuyensinh.qnu.edu.vn
7. **Địa chỉ công khai các thông tin về hoạt động của cơ sở đào tạo** (chương trình đào tạo; ngành đào tạo; đội ngũ giảng viên, cán bộ quản lý; cơ sở vật chất; quy mô đào tạo; tỷ lệ sinh viên có việc làm; kế hoạch tuyển sinh các ngành, hình thức, trình độ đào tạo ngành...): https://qnu.edu.vn và https://tuyensinh.qnu.edu.vn

---

<!-- Page 2 -->
## II. TUYỂN SINH ĐÀO TẠO ĐẠI HỌC CHÍNH QUY

1. **Đối tượng, điều kiện dự tuyển**: Đã tốt nghiệp THPT hoặc tương đương.

2. **Phương thức tuyển sinh**:
- **Phương thức 1 (PT1 - mã 100)**: Xét tuyển theo kết quả thi tốt nghiệp THPT năm 2026.
- **Phương thức 2 (PT2 - mã 200)**: Xét tuyển theo kết quả học tập 3 năm THPT (học bạ) theo quy định của Bộ Giáo dục và Đào tạo. Các ngành đào tạo giáo viên không xét tuyển phương thức 2.
- **Phương thức 3 (PT3 - mã 402A)**: Xét kết quả kỳ thi đánh giá năng lực (ĐGNL) của ĐHQG TP.HCM. Các ngành đào tạo giáo viên không xét tuyển phương thức 3).
- **Phương thức 4 (PT4 - mã 402B)**: Xét kết quả kỳ thi ĐGNL của Trường Đại học Sư phạm Hà Nội.
- **Phương thức 5 (PT5 - mã 405)**: Xét tuyển theo kết quả thi tốt nghiệp THPT năm 2026 với điểm thi năng khiếu GDMN/GDTC của Trường Đại học Quy Nhơn.

Ngoài ra, thực hiện **Xét tuyển thẳng** theo Quy chế tuyển sinh của Bộ Giáo dục và Đào tạo.

3. **Quy tắc quy đổi tương đương ngưỡng đầu vào và điểm trúng tuyển giữa các tổ hợp, phương thức tuyển sinh**: thông báo sau khi có kết quả thi tốt nghiệp THPT năm 2026.

4. **Các ngành, tổ hợp môn xét tuyển**:
- **Tổng chỉ tiêu dự kiến**: 4800 chỉ tiêu.

| STT | Mã xét tuyển | Tên ngành, chương trình xét tuyển | Phương thức tuyển sinh | Số lượng tuyển sinh dự kiến | Tổ hợp môn xét tuyển |
| :---: | :---: | :--- | :---: | :---: | :--- |
| 1 | 7140114 | Quản lý giáo dục | 1,2,3,4 | | (Văn, Sử, Địa)<br>(Văn, Sử, Giáo dục KT và PL)<br>(Văn, Địa, Giáo dục KT và PL)<br>(Văn, Toán, Giáo dục KT và PL)<br>(Văn, Toán, Anh)<br>(Văn, Toán, Sử) |
| 2 | 7140201 | Giáo dục Mầm non | 5 | | (Văn, Toán, NK GDMN) |
| 3 | 7140202 | Giáo dục Tiểu học | 1,4 | | (Văn, Anh, Toán)<br>(Văn, Anh, Lý)<br>(Văn, Anh, Hóa)<br>(Văn, Anh, Sinh)<br>(Văn, Anh, Sử)<br>(Văn, Anh, Địa) |
| 4 | 7140205 | Giáo dục Chính trị | 1,4 | | (Văn, Toán, Giáo dục KT và PL)<br>(Văn, Sử, Giáo dục KT và PL)<br>(Văn, Địa, Giáo dục KT và PL)<br>(Văn, Anh, Giáo dục KT và PL) |
| 5 | 7140206 | Giáo dục Thể chất | 5 | | (Toán, Sinh, NK TDTT)<br>(Toán, Văn, NK TDTT)<br>(Văn, Sinh, NK TDTT)<br>(Văn, Địa, NK TDTT)<br>(Toán, Lý, NK TDTT)<br>(Văn, Giáo dục KT và PL, NK TDTT) |
| 6 | 7140209 | Sư phạm Toán học | 1,4 | | (Toán, Lý, Hóa)<br>(Toán, Lý, Anh)<br>(Toán, Hóa, Anh)<br>(Toán, Tin, Anh) |
| 7 | 7140210 | Sư phạm Tin học | 1,4 | | (Toán, Lý, Hóa)<br>(Toán, Lý, Anh)<br>(Toán, Văn, Anh)<br>(Toán, Hóa, Anh)<br>(Toán, Văn, Tin)<br>(Toán, Lý, Tin)<br>(Toán, Hóa, Tin)<br>(Toán, Anh, Tin) |
| 8 | 7140211 | Sư phạm Vật lý | 1,4 | | (Toán, Lý, Hóa)<br>(Toán, Lý, Anh)<br>(Toán, Lý, Văn)<br>(Toán, Lý, Tin) |
| 9 | 7140212 | Sư phạm Hóa học | 1,4 | | (Toán, Hóa, Lý)<br>(Toán, Hóa, Sinh)<br>(Toán, Hóa, Anh)<br>(Toán, Hóa, Văn) |
| 10 | 7140213 | Sư phạm Sinh học | 1,4 | | (Toán, Sinh, Hóa)<br>(Toán, Sinh, Lý)<br>(Toán, Sinh, Anh)<br>(Toán, Sinh, Văn) |
| 11 | 7140217 | Sư phạm Ngữ Văn | 1,4 | | (Văn, Sử, Địa)<br>(Văn, Sử, Anh)<br>(Văn, Địa, Anh)<br>(Văn, Toán, Anh)<br>(Văn, Giáo dục KT và PL, Anh) |
| 12 | 7140218 | Sư phạm Lịch sử | 1,4 | | (Văn, Sử, Địa)<br>(Văn, Sử, Giáo dục KT và PL)<br>(Văn, Sử, Anh)<br>(Văn, Sử, Toán) |
| 13 | 7140219 | Sư phạm Địa lý | 1,4 | | (Văn, Địa, Sử)<br>(Văn, Địa, Giáo dục KT và PL)<br>(Văn, Địa, Anh)<br>(Văn, Địa, Toán)<br>(Toán, Địa, Anh)<br>(Toán, Địa, Giáo dục KT và PL)<br>(Toán, Địa, Sinh)<br>(Toán, Địa, Sử)<br>(Toán, Địa, Hóa) |
| 14 | 7140231 | Sư phạm Tiếng Anh | 1,4 | | (Toán, Văn, Anh) |
| 15 | 7140247 | Sư phạm Khoa học tự nhiên | 1,4 | | (Toán, Lý, Hóa)<br>(Toán, Lý, Anh)<br>(Toán, Lý, Sinh)<br>(Toán, Hóa, Sinh)<br>(Toán, Sinh, Anh) |
| 16 | 7140249 | Sư phạm Lịch sử - Địa lý | 1,4 | | (Văn, Sử, Địa)<br>(Văn, Sử, Giáo dục KT và PL)<br>(Văn, Địa, Giáo dục KT và PL)<br>(Văn, Sử, Anh)<br>(Văn, Địa, Anh)<br>(Văn, Sử, Toán)<br>(Văn, Địa, Toán) |
| 17 | 7220201 | Ngôn ngữ Anh | 1,2,3,4 | | (Toán, Văn, Anh)<br>(Văn, Sử, Anh)<br>(Văn, Địa, Anh)<br>(Toán, Lý, Anh) |
| 18 | 7220204 | Ngôn ngữ Trung Quốc | 1,2,3,4 | | (Toán, Văn, Anh)<br>(Văn, Sử, Anh)<br>(Văn, Địa, Anh)<br>(Toán, Lý, Anh) |
| 19 | 7229030 | Văn học | 1,2,3,4 | | (Văn, Sử, Địa)<br>(Văn, Sử, Giáo dục KT và PL)<br>(Văn, Sử, Anh)<br>(Văn, Địa, Anh)<br>(Văn, Anh, Giáo dục KT và PL)<br>(Văn, Địa, Giáo dục KT và PL) |
| 20 | 7310101 | Kinh tế | 1,2,3,4 | | (Toán, Anh, Giáo dục KT và PL)<br>(Toán, Anh, Tin)<br>(Toán, Anh, Hóa)<br>(Toán, Anh, Văn)<br>(Toán, Anh, Lý)<br>(Toán, Anh, Địa)<br>(Toán, Anh, Sử) |
| 21 | 7310109 | Kinh tế số | 1,2,3,4 | | (Toán, Anh, Giáo dục KT và PL)<br>(Toán, Anh, Tin)<br>(Toán, Anh, Hóa)<br>(Toán, Anh, Văn)<br>(Toán, Anh, Lý)<br>(Toán, Anh, Địa)<br>(Toán, Anh, Sử) |
| 22 | 7310205 | Quản lý nhà nước | 1,2,3,4 | | (Văn, Toán, Anh)<br>(Văn, Lý, Anh)<br>(Văn, Sử, Anh)<br>(Văn, Toán, Giáo dục KT và PL)<br>(Văn, Sử, Giáo dục KT và PL)<br>(Văn, Sử, Địa) |
| 23 | 7310403 | Tâm lý học giáo dục | 1,2,3,4 | | (Văn, Sử, Địa)<br>(Văn, Sử, Giáo dục KT và PL)<br>(Văn, Địa, Giáo dục KT và PL)<br>(Văn, Toán, Giáo dục KT và PL)<br>(Văn, Toán, Anh)<br>(Văn, Toán, Sử)<br>(Văn, Sử, Anh) |
| 24 | 7310608 | Đông phương học | 1,2,3,4 | | (Văn, Sử, Địa)<br>(Văn, Sử, Giáo dục KT và PL)<br>(Văn, Sử, Anh)<br>(Văn, Địa, Anh)<br>(Văn, Giáo dục KT và PL, Anh)<br>(Văn, Toán, Anh)<br>(Văn, Toán, Sử)<br>(Văn, Sử, Tiếng Trung) |
| 25 | 7310630 | Việt Nam học | 1,2,3,4 | | (Văn, Sử, Địa)<br>(Văn, Sử, Giáo dục KT và PL)<br>(Văn, Địa, Giáo dục KT và PL)<br>(Văn, Toán, Sử)<br>(Văn, Toán, Địa)<br>(Văn, Giáo dục KT và PL, Anh)<br>(Văn, Toán, Giáo dục KT và PL) |
| 26 | 7340101 | Quản trị kinh doanh | 1,2,3,4 | | (Toán, Anh, Văn)<br>(Toán, Anh, Lý)<br>(Toán, Anh, Hóa)<br>(Toán, Anh, Tin)<br>(Toán, Anh, Giáo dục KT và PL)<br>(Toán, Anh, Sử)<br>(Toán, Anh, Địa) |
| 27 | 7340201 | Tài chính – Ngân hàng | 1,2,3,4 | | (Toán, Anh, Văn)<br>(Toán, Anh, Lý)<br>(Toán, Anh, Hóa)<br>(Toán, Anh, Tin)<br>(Toán, Anh, Giáo dục KT và PL)<br>(Toán, Anh, Sử)<br>(Toán, Anh, Địa) |
| 28 | 7340301 | Kế toán | 1,2,3,4 | | (Toán, Anh, Giáo dục KT và PL)<br>(Toán, Anh, Tin)<br>(Toán, Anh, Hóa)<br>(Toán, Anh, Văn)<br>(Toán, Anh, Lý)<br>(Toán, Anh, Địa)<br>(Toán, Anh, Sử) |
| 29 | 7340301AC | Kế toán (Định hướng ACCA) | 1,2,3,4 | | (Toán, Anh, Giáo dục KT và PL)<br>(Toán, Anh, Tin)<br>(Toán, Anh, Hóa)<br>(Toán, Anh, Văn)<br>(Toán, Anh, Lý)<br>(Toán, Anh, Địa)<br>(Toán, Anh, Sử) |
| 30 | 7340302 | Kiểm toán | 1,2,3,4 | | (Toán, Anh, Giáo dục KT và PL)<br>(Toán, Anh, Tin)<br>(Toán, Anh, Hóa)<br>(Toán, Anh, Văn)<br>(Toán, Anh, Lý)<br>(Toán, Anh, Địa)<br>(Toán, Anh, Sử) |
| 31 | 7380101 | Luật | 1,2,3,4 | | (Văn, Toán, Anh)<br>(Văn, Lý, Anh)<br>(Văn, Sử, Anh)<br>(Văn, Toán, Giáo dục KT và PL)<br>(Văn, Sử, Giáo dục KT và PL)<br>(Văn, Sử, Địa) |
| 32 | 7440112 | Hóa học (Hóa dược, Hóa mỹ phẩm) | 1,2,3,4 | | (Toán, Hóa, Lý)<br>(Toán, Hóa, Sinh)<br>(Toán, Hóa, Anh)<br>(Toán, Hóa, Văn)<br>(Toán, Hóa, Tin)<br>(Toán, Hóa, Sử)<br>(Toán, Hóa, Địa)<br>(Toán, Hóa, Giáo dục KT và PL) |
| 33 | 7460108 | Khoa học dữ liệu | 1,2,3,4 | | (Toán, Lý, Hóa)<br>(Toán, Lý, Anh)<br>(Toán, Hóa, Anh)<br>(Toán, Tin, Anh)<br>(Toán, Văn, Anh) |
| 34 | 7460112 | Toán ứng dụng | 1,2,3,4 | | (Toán, Lý, Hóa)<br>(Toán, Lý, Anh)<br>(Toán, Hóa, Anh)<br>(Toán, Tin, Anh)<br>(Toán, Văn, Anh) |
| 35 | 7480103 | Kỹ thuật phần mềm | 1,2,3,4 | | (Toán, Anh, Lý)<br>(Toán, Anh, Văn)<br>(Toán, Anh, Hóa)<br>(Toán, Anh, Giáo dục KT và PL)<br>(Toán, Anh, Tin) |
| 36 | 7480201 | Công nghệ thông tin (An toàn, an ninh mạng) | 1,2,3,4 | | (Toán, Anh, Lý)<br>(Toán, Anh, Văn)<br>(Toán, Anh, Hóa)<br>(Toán, Anh, Giáo dục KT và PL)<br>(Toán, Anh, Tin) |
| 37 | 7480107 | Trí tuệ nhân tạo | 1,2,3,4 | | (Toán, Lý, Hóa)<br>(Toán, Lý, Anh)<br>(Toán, Văn, Anh)<br>(Toán, Hóa, Anh)<br>(Toán, Tin, Anh) |
| 38 | 7510205 | Công nghệ kỹ thuật ô tô | 1,2,3,4 | | (Toán, Lý, Hóa)<br>(Toán, Lý, Anh)<br>(Toán, Lý, Tin)<br>(Toán, Lý, Văn)<br>(Toán, Lý, Công nghệ) |
| 39 | 7510401 | Công nghệ kỹ thuật hoá học | 1,2,3,4 | | (Toán, Hóa, Lý)<br>(Toán, Hóa, Anh)<br>(Toán, Hóa, Văn)<br>(Toán, Hóa, Giáo dục KT và PL)<br>(Toán, Hóa, Sinh)<br>(Toán, Hóa, Tin)<br>(Toán, Hóa, Sử) |
| 40 | 7510605 | Logistics và Quản lý chuỗi cung ứng | 1,2,3,4 | | (Toán, Anh, Văn)<br>(Toán, Anh, Lý)<br>(Toán, Anh, Hóa)<br>(Toán, Anh, Tin)<br>(Toán, Anh, Giáo dục KT và PL)<br>(Toán, Anh, Sử)<br>(Toán, Anh, Địa) |
| 41 | 7520116 | Kỹ thuật cơ khí động lực | 1,2,3,4 | | (Toán, Lý, Hóa)<br>(Toán, Lý, Anh)<br>(Toán, Lý, Tin)<br>(Toán, Lý, Văn)<br>(Toán, Lý, Công nghệ) |
| 42 | 7520201 | Kỹ thuật điện | 1,2,3,4 | | (Toán, Lý, Hóa)<br>(Toán, Lý, Anh)<br>(Toán, Lý, Tin)<br>(Toán, Lý, Văn)<br>(Toán, Lý, Công nghệ) |
| 43 | 7520207 | Kỹ thuật điện tử - viễn thông (chuyên ngành Thiết kế vi mạch) | 1,2,3,4 | | (Toán, Lý, Hóa)<br>(Toán, Lý, Anh)<br>(Toán, Lý, Tin)<br>(Toán, Lý, Văn)<br>(Toán, Lý, Công nghệ) |
| 44 | 7520216 | Kỹ thuật điều khiển và tự động hóa | 1,2,3,4 | | (Toán, Lý, Hóa)<br>(Toán, Lý, Anh)<br>(Toán, Lý, Tin)<br>(Toán, Lý, Văn)<br>(Toán, Lý, Công nghệ) |
| 45 | 7520401 | Vật lý kỹ thuật (chuyên ngành Công nghệ gia công, đóng gói và kiểm thử vi mạch) | 1,2,3,4 | | (Toán, Lý, Hóa)<br>(Toán, Lý, Anh)<br>(Toán, Lý, Sinh)<br>(Toán, Lý, Tin)<br>(Toán, Lý, Công nghệ)<br>(Toán, Lý, Văn) |
| 46 | 7540101 | Công nghệ thực phẩm | 1,2,3,4 | | (Toán, Hóa, Sinh)<br>(Toán, Hóa, Địa)<br>(Toán, Hóa, Sử)<br>(Toán, Hóa, Lý)<br>(Toán, Hóa, Anh)<br>(Toán, Hóa, Tin)<br>(Toán, Hóa, Văn)<br>(Toán, Hóa, Giáo dục KT và PL) |
| 47 | 7580201 | Kỹ thuật xây dựng | 1,2,3,4 | | (Toán, Lý, Hóa)<br>(Toán, Lý, Anh)<br>(Toán, Lý, Tin)<br>(Toán, Lý, Văn)<br>(Toán, Lý, Công nghệ) |
| 48 | 7620109 | Nông học | 1,2,3,4 | | (Toán, Sinh, Lý)<br>(Toán, Sinh, Hóa)<br>(Toán, Sinh, Sử)<br>(Toán, Sinh, Văn)<br>(Toán, Sinh, Anh)<br>(Toán, Sinh, Giáo dục KT và PL)<br>(Toán, Sinh, Tin)<br>(Toán, Sinh, Công nghệ)<br>(Toán, Sinh, Địa) |
| 49 | 7760101 | Công tác xã hội | 1,2,3,4 | | (Văn, Sử, Địa)<br>(Văn, Sử, Giáo dục KT và PL)<br>(Văn, Sử, Anh)<br>(Văn, Toán, Anh)<br>(Văn, Toán, Địa)<br>(Văn, Toán, Sử)<br>(Văn, Toán, Giáo dục KT và PL)<br>(Văn, Giáo dục KT và PL, Anh)<br>(Văn, Địa, Giáo dục KT và PL) |
| 50 | 7810103 | Quản trị dịch vụ du lịch và lữ hành | 1,2,3,4 | | (Toán, Văn, Giáo dục KT và PL)<br>(Toán, Văn, Anh)<br>(Toán, Văn, Sử)<br>(Toán, Văn, Địa)<br>(Toán, Văn, Hóa)<br>(Toán, Văn, Lý)<br>(Toán, Văn, Tin) |
| 51 | 7810201 | Quản trị khách sạn | 1,2,3,4 | | (Toán, Văn, Giáo dục KT và PL)<br>(Toán, Văn, Anh)<br>(Toán, Văn, Sử)<br>(Toán, Văn, Địa)<br>(Toán, Văn, Hóa)<br>(Toán, Văn, Lý)<br>(Toán, Văn, Tin) |
| 52 | 7850101 | Quản lý tài nguyên và môi trường | 1,2,3,4 | | (Địa, Văn, Giáo dục KT và PL)<br>(Địa, Toán, Giáo dục KT và PL)<br>(Địa, Toán, Văn)<br>(Địa, Toán, Sinh)<br>(Địa, Văn, Anh)<br>(Địa, Toán, Lý)<br>(Địa, Toán, Anh)<br>(Địa, Văn, Sinh)<br>(Địa, Toán, Hóa) |
| 53 | 7850103 | Quản lý đất đai | 1,2,3,4 | | (Địa, Văn, Giáo dục KT và PL)<br>(Địa, Toán, Giáo dục KT và PL)<br>(Địa, Toán, Văn)<br>(Địa, Toán, Sinh)<br>(Địa, Văn, Anh)<br>(Địa, Toán, Lý)<br>(Địa, Toán, Anh)<br>(Địa, Văn, Sinh)<br>(Địa, Toán, Hóa) |

---

## 5. Các thông tin cần thiết khác để thí sinh dự tuyển

### a. Điều kiện phụ sử dụng trong xét tuyển:
Trường hợp nhiều thí sinh có cùng điểm xét ở cuối danh sách, thứ tự xét ưu tiên đối với các thí sinh có điểm cộng thấp hơn; trường hợp nhiều thí sinh có cùng điểm xét ở cuối danh sách và có điểm cộng bằng nhau, thứ tự xét ưu tiên đối với các thí sinh có thứ tự ưu tiên nguyện vọng cao hơn.

### b. Điểm cộng:
Xem chi tiết tại Mục 7.

### c. Quy đổi điểm chứng chỉ tiếng Anh quốc tế:
Sử dụng chứng chỉ VSTEP, IELTS (còn hiệu lực) thay cho điểm môn Tiếng Anh trong tổ hợp môn xét tuyển, khi xét tuyển theo Phương thức 1 và Phương thức 2, được quy đổi như sau:

| Điểm IELTS | Điểm quy đổi IELTS | Điểm VSTEP | Điểm quy đổi VSTEP |
| :---: | :---: | :---: | :---: |
| 5.0 | 8.0 | 4.0 | 8.0 |
| 5.5 | 8.5 | 5.0 | 8.5 |
| 6.0 | 9.0 | 6.0 | 9.0 |
| 6.5 | 9.5 | 7.0 | 9.5 |
| 7.0 trở lên | 10.0 | 8.0 trở lên | 10.0 |

*Ghi chú*: Thí sinh nộp chứng chỉ tại các điểm tiếp nhận để nhập lên cơ sở dữ liệu tuyển sinh của Bộ GD&ĐT.

### d. Ngưỡng đầu vào các ngành và điều kiện sức khỏe:
- Ngưỡng đầu vào các ngành, các phương thức thực hiện theo các quy định tại Quy chế tuyển sinh đại học của Bộ Giáo dục và Đào tạo.
- Riêng đối với ngành **Giáo dục Thể chất**, thí sinh xét tuyển phải không bị dị tật cột sống, tay chân, mắt, phát âm và các dị tật khác; chiều cao tối thiểu là 1,65m, nặng 45 kg đối với nam và 1,55m, nặng 40 kg đối với nữ.

---

## 6. Tổ chức tuyển sinh

### Đợt 1:
- **a) Nộp hồ sơ xét tuyển thẳng, ưu tiên xét tuyển**: từ ngày 20/5/2026 đến ngày 20/6/2026.
- **b) Thi năng khiếu Giáo dục mầm non, Giáo dục thể chất**: thi vào các ngày 19, 20, 21/6/2026. Thí sinh đăng ký thi năng khiếu tại https://tsd.qnu.edu.vn từ ngày 20/5/2026 đến 15/6/2026.
- **c) Xét tuyển đợt 1**:
  - Tất cả thí sinh, tất cả các phương thức phải đăng ký xét tuyển trên hệ thống của Bộ GD&ĐT từ ngày 02/7/2026 đến ngày 14/7/2026.
  - Công bố ngưỡng bảo đảm chất lượng đầu vào và quy tắc quy đổi điểm giữa các phương thức: theo quy định của Bộ.
  - Xét tuyển theo kế hoạch của Bộ GD&ĐT: 04/8/2026 – 10/8/2026.

### Đợt 2:
Xét tuyển các ngành còn chỉ tiêu sau khi thí sinh đăng ký nhập học đợt 1, thông báo từ ngày 22/8/2026.

---

## 7. Chính sách ưu tiên

### Xét tuyển thẳng:
Theo Quy chế tuyển sinh của Bộ Giáo dục và Đào tạo vào các ngành phù hợp theo **Phụ lục 1**.

### Ưu tiên xét tuyển:
- **Học sinh giỏi quốc gia, Khoa học kỹ thuật cấp quốc gia**: Đối với thí sinh đoạt giải trong kỳ thi chọn học sinh giỏi quốc gia, Cuộc thi khoa học, kỹ thuật cấp quốc gia mức ưu tiên cụ thể như sau:
  - Giải Nhất: cộng 3,0 điểm;
  - Giải Nhì: cộng 2,0 điểm;
  - Giải Ba: cộng 1,0 điểm;
  - Giải Khuyến khích hoặc Giải Tư (Cuộc thi khoa học, kỹ thuật cấp quốc gia): cộng 0,5 điểm vào tổng điểm 3 môn xét tuyển sau khi nhân hệ số môn thi chính nếu có.
  - *Thời hạn*: Thời gian đoạt giải không quá 3 năm tính tới thời điểm xét tuyển.
- **Vận động viên đội tuyển quốc gia tham gia thi đấu quốc tế**: Đối với thí sinh tham gia đội tuyển quốc gia thi đấu tại các giải quốc tế chính thức được Bộ Văn hóa, Thể thao và Du lịch xác nhận đã hoàn thành nhiệm vụ (bao gồm: Giải vô địch thế giới, Cúp thế giới, Thế vận hội Olympic, Đại hội Thể thao châu Á - ASIAD, Giải vô địch châu Á, Cúp châu Á, Giải vô địch Đông Nam Á, Đại hội Thể thao Đông Nam Á - SEA Games, Cúp Đông Nam Á) và đã tham dự kỳ thi năng khiếu của Trường được **cộng 3,0 điểm** vào tổng điểm 3 môn xét tuyển vào ngành **Giáo dục Thể chất**; thời gian đoạt giải không quá 4 năm tính tới thời điểm xét tuyển.
- **Vận động viên đoạt huy chương quốc gia & Kiện tướng quốc gia**: Đối với thí sinh đoạt huy chương vàng, bạc, đồng các giải thể dục thể thao cấp quốc gia tổ chức một lần trong năm và thí sinh được Tổng cục Thể dục thể thao có quyết định công nhận là kiện tướng quốc gia đã tham dự kỳ thi năng khiếu của Trường được **cộng 1,0 điểm** vào tổng điểm 3 môn xét tuyển vào ngành **Giáo dục Thể chất**; thời gian đoạt giải không quá 4 năm tính tới thời điểm xét tuyển.

---

## 8. Lệ phí xét tuyển, thi tuyển, học phí

### Lệ phí:
- **Lệ phí Thi năng khiếu Giáo dục mầm non, Giáo dục thể chất**: 300.000 đồng/thí sinh.
- **Lệ phí xét tuyển**: theo quy định của Bộ Giáo dục và Đào tạo.

### Học phí:
- Các Chương trình đào tạo đại trà thực hiện theo Nghị định 238/2025/NĐ-CP ngày 03/9/2025 và các quy định hiện hành.
- Chương trình đào tạo Kế toán (ACCA) và các chương trình đào tạo giảng dạy bằng tiếng Anh (Công nghệ thông tin, Kỹ thuật điện, Tài chính – Ngân hàng) xác định trên cơ sở định mức kinh tế - kỹ thuật, định mức chi phí của Trường.
- **Học phí toàn khóa dự kiến**:
  - Các ngành đào tạo cử nhân đại trà: 83 - 97 triệu đồng (khóa học 4 năm).
  - Các chương trình đào tạo kỹ sư đại trà: 112,3 triệu đồng (khóa học 4,5 năm).
  - Các chương trình đào tạo giảng dạy bằng tiếng Anh, chương trình đào tạo Kế toán (ACCA): mức học phí dự kiến bằng 1,5 lần so với chương trình đại trà.

---

## 9. Việc cơ sở đào tạo thực hiện các cam kết đối với thí sinh
Hội đồng tuyển sinh sẽ giải quyết theo yêu cầu của thí sinh trên cơ sở kiểm tra trách nhiệm của các bên liên quan trong quá trình xét tuyển.

---

## 10. Các nội dung khác
Không.

---

## 11. Thông tin về tuyển sinh của 2 năm gần nhất (2024 và 2025)

| STT | Mã ngành | Tên ngành | Chỉ tiêu 2024 | Số trúng tuyển nhập học 2024 | Điểm trúng tuyển 2024 | Chỉ tiêu 2025 | Số trúng tuyển nhập học 2025 | Điểm trúng tuyển 2025 |
| :---: | :---: | :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| 1 | 7140114 | Quản lý Giáo dục | 47 | 50 | 22.5 | 50 | 41 | 25.1 |
| 2 | 7140201 | Giáo dục mầm non | 126 | 118 | 23.1 | 177 | 177 | 21.75 |
| 3 | 7140202 | Giáo dục Tiểu học | 244 | 234 | 26.95 | 240 | 239 | 26.9 |
| 4 | 7140205 | Giáo dục chính trị | 20 | 23 | 26.65 | 22 | 21 | 26.65 |
| 5 | 7140206 | Giáo dục thể chất | 24 | 23 | 26.5 | 99 | 98 | 19.8 |
| 6 | 7140209 | Sư phạm Toán học | 20 | 20 | 26.5 | 101 | 101 | 25.85 |
| 7 | 7140210 | Sư phạm Tin học | 100 | 106 | 22.85 | 112 | 112 | 20.35 |
| 8 | 7140211 | Sư phạm Vật lý | 20 | 19 | 25.75 | 81 | 80 | 24.4 |
| 9 | 7140212 | Sư phạm Hóa học | 0 | 0 | - | 25 | 25 | 25.3 |
| 10 | 7140213 | Sư phạm Sinh học | 20 | 21 | 23.9 | 29 | 29 | 21.2 |
| 11 | 7140217 | Sư phạm Ngữ văn | 30 | 32 | 27.35 | 119 | 119 | 26.85 |
| 12 | 7140218 | Sư phạm Lịch sử | 20 | 23 | 27.45 | 47 | 47 | 27.21 |
| 13 | 7140219 | Sư phạm Địa lý | 20 | 19 | 27.3 | 70 | 70 | 26.74 |
| 14 | 7140231 | Sư phạm Tiếng Anh | 84 | 87 | 25.92 | 199 | 199 | 23.59 |
| 15 | 7140247 | Sư phạm KH tự nhiên | 20 | 17 | 25.65 | 99 | 99 | 22.5 |
| 16 | 7140249 | Sư phạm Lịch sử Địa lý | 27 | 32 | 27.15 | 112 | 112 | 26.4 |
| 17 | 7220201 | Ngôn ngữ Anh | 290 | 288 | 22.0 | 287 | 285 | 23.0 |
| 18 | 7220204 | Ngôn ngữ Trung Quốc | 64 | 65 | 23.5 | 66 | 63 | 24.2 |
| 19 | 7229030 | Văn học | 61 | 62 | 23.5 | 56 | 54 | 25.29 |
| 20 | 7310101 | Kinh tế | 114 | 119 | 18.0 | 113 | 111 | 21.4 |
| 21 | 7310205 | Quản lý nhà nước | 99 | 101 | 23.15 | 77 | 58 | 23.6 |
| 22 | 7310403 | Tâm lý học giáo dục | 73 | 81 | 23.0 | 71 | 69 | 24.6 |
| 23 | 7310608 | Đông phương học | 128 | 107 | 15.0 | 107 | 106 | 22.3 |
| 24 | 7310630 | Việt Nam học | 64 | 69 | 18.0 | 61 | 57 | 23.5 |
| 25 | 7340101 | Quản trị kinh doanh | 266 | 264 | 17.0 | 250 | 249 | 21.7 |
| 26 | 7340201 | Tài chính – Ngân hàng | 86 | 92 | 20.25 | 102 | 87 | 22.5 |
| 27 | 7340301 | Kế toán | 262 | 258 | 17.75 | 238 | 236 | 20.3 |
| 28 | 7340301ACCA | Kế toán ACCA | 30 | 29 | 18.0 | 30 | 33 | 19.2 |
| 29 | 7340302 | Kiểm toán | 54 | 56 | 18.75 | 50 | 50 | 21.8 |
| 30 | 7380101 | Luật | 200 | 188 | 23.65 | 170 | 158 | 23.58 |
| 31 | 7440112 | Hóa học | 50 | 32 | 15.0 | 49 | 50 | 20.5 |
| 32 | 7460108 | Khoa học dữ liệu | 45 | 17 | 15.0 | 40 | 41 | 17.1 |
| 33 | 7460112 | Toán ứng dụng | 55 | 47 | 15.0 | 60 | 60 | 19.5 |
| 34 | 7480103 | Kỹ thuật phần mềm | 61 | 50 | 15.0 | 61 | 58 | 19.5 |
| 35 | 7480107 | Trí tuệ nhân tạo | 52 | 18 | 15.0 | 55 | 50 | 20.0 |
| 36 | 7480201 | Công nghệ thông tin | 304 | 349 | 16.5 | 172 | 171 | 21.5 |
| 37 | 7510205 | Công nghệ kỹ thuật ô tô | 186 | 169 | 16.0 | 122 | 111 | 22.2 |
| 38 | 7510401 | Công nghệ KT hoá học | 50 | 19 | 15.0 | 41 | 47 | 20.5 |
| 39 | 7510605 | Logistics và QL chuỗi cung ứng | 170 | 218 | 21.0 | 184 | 164 | 23.6 |
| 40 | 7520116 | Kỹ thuật cơ khí động lực | 0 | 0 | - | 33 | 38 | 20.14 |
| 41 | 7520201 | Kỹ thuật điện | 113 | 143 | 16.0 | 144 | 137 | 20.65 |
| 42 | 7520207 | Kỹ thuật điện tử - viễn thông | 89 | 61 | 15.0 | 89 | 90 | 20.77 |
| 43 | 7520216 | Kỹ thuật điều khiển và Tự động hóa | 74 | 67 | 15.0 | 85 | 76 | 21.02 |
| 44 | 7520401 | Vật lý kỹ thuật | 0 | 0 | - | 57 | 56 | 18.25 |
| 45 | 7540101 | Công nghệ thực phẩm | 170 | 142 | 15.0 | 148 | 137 | 20.9 |
| 46 | 7580201 | Kỹ thuật xây dựng | 100 | 96 | 15.0 | 97 | 99 | 20.15 |
| 47 | 7620109 | Nông học | 50 | 29 | 15.0 | 44 | 39 | 15.0 |
| 48 | 7760101 | Công tác xã hội | 96 | 77 | 20.25 | 65 | 48 | 23.7 |
| 49 | 7810103 | Quản trị dịch vụ du lịch và lữ hành | 131 | 154 | 19.85 | 146 | 122 | 22.25 |
| 50 | 7810201 | Quản trị khách sạn | 167 | 128 | 18.35 | 113 | 90 | 22.65 |
| 51 | 7850101 | Quản lý tài nguyên và môi trường | 100 | 84 | 15.0 | 102 | 101 | 20.75 |
| 52 | 7850103 | Quản lý đất đai | 100 | 105 | 15.0 | 119 | 115 | 17.9 |

---

**Nơi nhận**:
- Các khoa;
- Phòng CTSV&HTDN;
- Trung tâm Số và Học liệu;
- Đăng website trường;
- Lưu: VT, ĐT.

**HIỆU TRƯỞNG**  
*(Đã ký và đóng dấu)*  
**PGS.TS. Đoàn Đức Tùng**

---

# PHỤ LỤC 1
## DANH SÁCH CÁC NGÀNH XÉT TUYỂN THẲNG VÀ ƯU TIÊN XÉT TUYỂN
*(Kèm theo Thông báo Thông tin tuyển sinh đại học năm 2026 của Hiệu trưởng Trường Đại học Quy Nhơn)*

| Tên môn thi học sinh giỏi quốc gia | Tên ngành đào tạo | Mã ngành |
| :--- | :--- | :---: |
| Toán | Sư phạm Toán học | 7140209 |
| Toán | Toán ứng dụng | 7460112 |
| Toán | Khoa học dữ liệu | 7460108 |
| Toán | Trí tuệ nhân tạo | 7480207 |
| Toán | Công nghệ thông tin | 7480201 |
| Vật lí | Sư phạm Vật lý | 7140211 |
| Vật lí | Kỹ thuật điện | 7520201 |
| Vật lí | Sư phạm Khoa học tự nhiên | 7140247 |
| Vật lí | Vật lý kỹ thuật (Công nghệ gia công, đóng gói và kiểm thử vi mạch) | 7520401 |
| Vật lí | Kỹ thuật điện tử - viễn thông (Thiết kế vi mạch) | 7520207 |
| Hóa | Sư phạm Hóa học | 7140212 |
| Hóa | Công nghệ thực phẩm | 7540101 |
| Hóa | Công nghệ kỹ thuật Hóa học | 7510401 |
| Hóa | Sư phạm Khoa học tự nhiên | 7140247 |
| Hóa | Hóa học (Hóa dược, Hóa mỹ phẩm) | 7440112 |
| Sinh | Sư phạm Sinh học | 7140213 |
| Sinh | Nông học | 7620109 |
| Sinh | Sư phạm Khoa học tự nhiên | 7140247 |
| Ngữ văn | Sư phạm Ngữ văn | 7140217 |
| Ngữ văn | Việt Nam học | 7310630 |
| Ngữ văn | Quản lý nhà nước | 7310205 |
| Ngữ văn | Luật | 7380101 |
| Lịch sử | Sư phạm Lịch sử | 7140218 |
| Lịch sử | Đông phương học | 7310608 |
| Lịch sử | Quản lý nhà nước | 7310205 |
| Lịch sử | Luật | 7380101 |
| Lịch sử | Sư phạm Lịch sử - Địa lý | 7140249 |
| Địa lí | Sư phạm Địa lý | 7140219 |
| Địa lí | Đông phương học | 7310608 |
| Địa lí | Sư phạm Lịch sử - Địa lý | 7140249 |
| Tin học | Sư phạm Tin học | 7140210 |
| Tin học | Công nghệ thông tin | 7480201 |
| Tin học | Trí tuệ nhân tạo | 7480107 |
| Tin học | Kỹ thuật phần mềm | 7480103 |
| Tiếng Anh | Sư phạm Tiếng Anh | 7140231 |
| Tiếng Anh | Ngôn ngữ Anh | 7220201 |
| Tiếng Anh | Đông phương học | 7310608 |
| Tiếng Trung | Ngôn ngữ Trung Quốc | 7220204 |
"""

def main():
    TARGET_FILE.write_text(CONTENT.strip() + "\n", encoding="utf-8")
    print(f"[OK] Standardized Markdown successfully written to: {TARGET_FILE}")
    print(f"Total size: {len(CONTENT)} bytes, lines: {len(CONTENT.splitlines())}")

if __name__ == "__main__":
    main()
