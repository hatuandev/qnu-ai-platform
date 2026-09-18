import type { DocumentVerificationData } from "@/types/knowledge";

/**
 * Dữ liệu bóc tách và đối soát đầy đủ 14 trang chuẩn hóa từ QNU-AI-Core.
 * Đồng bộ chính xác giữa ảnh scan thực tế (/ocr-cache/doc_ts_2026/page_N.jpg),
 * hộp bao Bounding Boxes, phân cấp Regions layout inspector,
 * và nội dung Markdown chuẩn GitHub-Flavored Markdown với bảng biểu nguyên bản.
 */
export const MOCK_VERIFICATION_DOCUMENT: DocumentVerificationData = {
  document_id: "doc_ts_2026",
  collection_id: "col_admissions",
  title: "Thông tin tuyển sinh đại học 2026 Lan2 1",
  filename: "Thong tin tuyen sinh dai hoc 2026_Lan2-1 (1).docx",
  file_size_mb: 0.87,
  total_pages: 14,
  engine: "docling-tableformer-local",
  total_chars: 21870,
  estimated_chunks: 37,
  pages: [
    {
      page_number: 1,
      word_count: 320,
      line_count: 34,
      image_url: "/ocr-cache/doc_ts_2026/page_1.jpg",
      markdown_content: `<!-- Trang 1 -->
> **BỘ GIÁO DỤC VÀ ĐÀO TẠO — TRƯỜNG ĐẠI HỌC QUY NHƠN**  
> *Số: /TB-ĐHQN*  
> **CỘNG HÒA XÃ HỘI CHỦ NGHĨA VIỆT NAM — Độc lập - Tự do - Hạnh phúc**  
> *Gia Lai, ngày     tháng     năm 2026*

---

# THÔNG BÁO
## THÔNG TIN TUYỂN SINH ĐẠI HỌC NĂM 2026 (CẬP NHẬT)
*Hình thức đào tạo: Chính quy*

*Căn cứ Quy chế Tuyển sinh các ngành đào tạo trình độ đại học và ngành Giáo dục mầm non trình độ cao đẳng ban hành kèm theo Thông tư số 06/2026/TT/TT-BGDĐT ngày 15/02/2026 của Bộ trưởng Bộ Giáo dục và Đào tạo;*

*Căn cứ Quy chế tuyển sinh đại học ban hành kèm theo Quyết định số /QĐ-ĐHQN ngày của Hiệu trưởng Trường Đại học Quy Nhơn;*

*Căn cứ Kế hoạch triển khai công tác tuyển sinh đại học, cao đẳng năm 2026 ban hành theo Quyết định số 3037/QĐ-BGDĐT ngày 3/11/2025 của Bộ Giáo dục và Đào tạo;*

*Căn cứ Công văn số 2304/BGDĐT-GDĐH ngày 04/5/2026 hướng dẫn tuyển sinh đại học, tuyển sinh cao đẳng 2026;*

Trường Đại học Quy Nhơn thông báo Thông tin tuyển sinh đại học năm 2026 (cập nhật) như sau:

### I. THÔNG TIN CHUNG
1. **Tên cơ sở đào tạo**: Trường Đại học Quy Nhơn
2. **Mã cơ sở đào tạo trong tuyển sinh**: DQN
3. **Địa chỉ**: 170 An Dương Vương, P. Quy Nhơn Nam, tỉnh Gia Lai
4. **Địa chỉ trang thông tin điện tử**: https://qnu.edu.vn
5. **Số điện thoại liên hệ tuyển sinh**: 1800.55.88.49
6. **Địa chỉ công khai quy chế tuyển sinh**: https://tuyensinh.qnu.edu.vn
7. **Địa chỉ công khai các thông tin về hoạt động của cơ sở đào tạo**: https://qnu.edu.vn và https://tuyensinh.qnu.edu.vn

### II. TUYỂN SINH ĐÀO TẠO ĐẠI HỌC CHÍNH QUY
1. **Đối tượng, điều kiện dự tuyển**: Đã tốt nghiệp THPT hoặc tương đương.
2. **Phương thức tuyển sinh**:`,
      raw_text: `<!-- Trang 1 --
 BỘ GIÁO DỤC VÀ ĐÀO TẠO — TRƯỜNG ĐẠI HỌC QUY NHƠN  
 Số: /TB-ĐHQN  
 CỘNG HÒA XÃ HỘI CHỦ NGHĨA VIỆT NAM — Độc lập - Tự do - Hạnh phúc  
 Gia Lai, ngày     tháng     năm 2026

---

 THÔNG BÁO
 THÔNG TIN TUYỂN SINH ĐẠI HỌC NĂM 2026 (CẬP NHẬT)
Hình thức đào tạo: Chính quy

Căn cứ Quy chế Tuyển sinh các ngành đào tạo trình độ đại học và ngành Giáo dục mầm non trình độ cao đẳng ban hành kèm theo Thông tư số 06/2026/TT/TT-BGDĐT ngày 15/02/2026 của Bộ trưởng Bộ Giáo dục và Đào tạo;

Căn cứ Quy chế tuyển sinh đại học ban hành kèm theo Quyết định số /QĐ-ĐHQN ngày của Hiệu trưởng Trường Đại học Quy Nhơn;

Căn cứ Kế hoạch triển khai công tác tuyển sinh đại học, cao đẳng năm 2026 ban hành theo Quyết định số 3037/QĐ-BGDĐT ngày 3/11/2025 của Bộ Giáo dục và Đào tạo;

Căn cứ Công văn số 2304/BGDĐT-GDĐH ngày 04/5/2026 hướng dẫn tuyển sinh đại học, tuyển sinh cao đẳng 2026;

Trường Đại học Quy Nhơn thông báo Thông tin tuyển sinh đại học năm 2026 (cập nhật) như sau:

 I. THÔNG TIN CHUNG
1. Tên cơ sở đào tạo: Trường Đại học Quy Nhơn
2. Mã cơ sở đào tạo trong tuyển sinh: DQN
3. Địa chỉ: 170 An Dương Vương, P. Quy Nhơn Nam, tỉnh Gia Lai
4. Địa chỉ trang thông tin điện tử: https://qnu.edu.vn
5. Số điện thoại liên hệ tuyển sinh: 1800.55.88.49
6. Địa chỉ công khai quy chế tuyển sinh: https://tuyensinh.qnu.edu.vn
7. Địa chỉ công khai các thông tin về hoạt động của cơ sở đào tạo: https://qnu.edu.vn và https://tuyensinh.qnu.edu.vn

 II. TUYỂN SINH ĐÀO TẠO ĐẠI HỌC CHÍNH QUY
1. Đối tượng, điều kiện dự tuyển: Đã tốt nghiệp THPT hoặc tương đương.
2. Phương thức tuyển sinh:`,
      bounding_boxes: [
        {
          id: "bbox_p1_01",
          page_number: 1,
          type: "text",
          coordinates: {
            x: 17.8,
            y: 7.9,
            width: 74.7,
            height: 6.5,
          },
          label: "header",
          confidence: 0.98,
          content_snippet: "Tiêu đề đầu trang",
        },
        {
          id: "bbox_p1_02",
          page_number: 1,
          type: "text",
          coordinates: {
            x: 22.1,
            y: 18.2,
            width: 60.4,
            height: 5.3,
          },
          label: "title",
          confidence: 0.98,
          content_snippet: "Tên loại văn bản / Trích yếu nội dung",
        },
        {
          id: "bbox_p1_03",
          page_number: 1,
          type: "text",
          coordinates: {
            x: 14.3,
            y: 26.2,
            width: 76.0,
            height: 61.7,
          },
          label: "text",
          confidence: 0.98,
          content_snippet: "Đoạn văn bản quy định",
        },
        {
          id: "bbox_p1_04",
          page_number: 1,
          type: "text",
          coordinates: {
            x: 19.1,
            y: 89.2,
            width: 23.6,
            height: 1.1,
          },
          label: "list",
          confidence: 0.98,
          content_snippet: "Nơi nhận / Danh sách đơn vị phối hợp",
        },
      ],
      regions: [
        {
          id: "reg_p1_01",
          page_number: 1,
          title: "Tiêu đề Cơ quan & Quốc hiệu Tiêu ngữ",
          type: "header",
          confidence: 0.99,
          reading_order: 1,
          details: "BỘ GIÁO DỤC VÀ ĐÀO TẠO — TRƯỜNG ĐẠI HỌC QUY NHƠN",
        },
        {
          id: "reg_p1_02",
          page_number: 1,
          title: "Thông báo Tuyển sinh Đại học 2026",
          type: "text",
          confidence: 0.98,
          reading_order: 2,
          details: "Heading 1 - Thông tin tuyển sinh đại học chính quy 2026",
        },
        {
          id: "reg_p1_03",
          page_number: 1,
          title: "Căn cứ Pháp lý Tuyển sinh (4 Căn cứ)",
          type: "text",
          confidence: 0.97,
          reading_order: 3,
          details: "Thông tư 06/2026, Quyết định ĐHQN, QĐ 3037 và CV 2304 BGDĐT",
        },
        {
          id: "reg_p1_04",
          page_number: 1,
          title: "I. Thông tin chung & Hotline Trường",
          type: "text",
          confidence: 0.98,
          reading_order: 4,
          details: "7 mục công khai thông tin theo quy định BGDĐT",
        },
        {
          id: "reg_p1_05",
          page_number: 1,
          title: "II. Tuyển sinh Đào tạo Đại học Chính quy",
          type: "text",
          confidence: 0.98,
          reading_order: 5,
          details: "Đối tượng, điều kiện dự tuyển và phương thức tuyển sinh",
        },
      ],
    },
    {
      page_number: 2,
      word_count: 374,
      line_count: 21,
      image_url: "/ocr-cache/doc_ts_2026/page_2.jpg",
      markdown_content: `<!-- Trang 2 -->
+ **Phương thức 1 (PT1 - mã 100)**: Xét tuyển theo kết quả thi tốt nghiệp THPT năm 2026.
+ **Phương thức 2 (PT2 - mã 200)**: Xét tuyển theo kết quả học tập 3 năm THPT (học bạ) theo quy định của Bộ Giáo dục và Đào tạo. Các ngành đào tạo giáo viên không xét tuyển phương thức 2.
+ **Phương thức 3 (PT3 - mã 402A)**: Xét kết quả kỳ thi đánh giá năng lực (ĐGNL) của ĐHQG TP.HCM. Các ngành đào tạo giáo viên không xét tuyển phương thức 3.
+ **Phương thức 4 (PT4 - mã 402B)**: Xét kết quả kỳ thi ĐGNL của Trường Đại học Sư phạm Hà Nội.
+ **Phương thức 5 (PT5 - mã 405)**: Xét tuyển theo kết quả thi tốt nghiệp THPT năm 2026 với điểm thi năng khiếu GDMN/GDTC của Trường Đại học Quy Nhơn.

Ngoài ra, thực hiện Xét tuyển thẳng theo Quy chế tuyển sinh của Bộ Giáo dục và Đào tạo.

**3. Quy tắc quy đổi tương đương ngưỡng đầu vào và điểm trúng tuyển giữa các tổ hợp, phương thức tuyển sinh**: thông báo sau khi có kết quả thi tốt nghiệp THPT năm 2026.

**4. Các ngành, tổ hợp môn xét tuyển**:  
Tổng chỉ tiêu dự kiến: **4800 chỉ tiêu**.

| STT | Mã xét tuyển | Tên ngành, chương trình xét tuyển | Phương thức tuyển sinh | Số lượng dự kiến | Tổ hợp môn xét tuyển |
| :---: | :---: | :--- | :---: | :---: | :--- |
| 1 | 7140114 | Quản lý Giáo dục | 47 | 50 | 22.5 | 50 | 41 | 25.1 |
| 2 | 7140201 | Giáo dục mầm non | 126 | 118 | 23.1 | 177 | 177 | 21.75 |
| 3 | 7140202 | Giáo dục Tiểu học | 244 | 234 | 26.95 | 240 | 239 | 26.9 |
| 4 | 7140205 | Giáo dục chính trị | 20 | 23 | 26.65 | 22 | 21 | 26.65 |
| 5 | 7140206 | Giáo dục thể chất | 24 | 23 | 26.5 | 99 | 98 | 19.8 |`,
      raw_text: `<!-- Trang 2 --
+ Phương thức 1 (PT1 - mã 100): Xét tuyển theo kết quả thi tốt nghiệp THPT năm 2026.
+ Phương thức 2 (PT2 - mã 200): Xét tuyển theo kết quả học tập 3 năm THPT (học bạ) theo quy định của Bộ Giáo dục và Đào tạo. Các ngành đào tạo giáo viên không xét tuyển phương thức 2.
+ Phương thức 3 (PT3 - mã 402A): Xét kết quả kỳ thi đánh giá năng lực (ĐGNL) của ĐHQG TP.HCM. Các ngành đào tạo giáo viên không xét tuyển phương thức 3.
+ Phương thức 4 (PT4 - mã 402B): Xét kết quả kỳ thi ĐGNL của Trường Đại học Sư phạm Hà Nội.
+ Phương thức 5 (PT5 - mã 405): Xét tuyển theo kết quả thi tốt nghiệp THPT năm 2026 với điểm thi năng khiếu GDMN/GDTC của Trường Đại học Quy Nhơn.

Ngoài ra, thực hiện Xét tuyển thẳng theo Quy chế tuyển sinh của Bộ Giáo dục và Đào tạo.

3. Quy tắc quy đổi tương đương ngưỡng đầu vào và điểm trúng tuyển giữa các tổ hợp, phương thức tuyển sinh: thông báo sau khi có kết quả thi tốt nghiệp THPT năm 2026.

4. Các ngành, tổ hợp môn xét tuyển:  
Tổng chỉ tiêu dự kiến: 4800 chỉ tiêu.

 STT  Mã xét tuyển  Tên ngành, chương trình xét tuyển  Phương thức tuyển sinh  Số lượng dự kiến  Tổ hợp môn xét tuyển 
 :---:  :---:  :---  :---:  :---:  :--- 
 1  7140114  Quản lý Giáo dục  47  50  22.5  50  41  25.1 
 2  7140201  Giáo dục mầm non  126  118  23.1  177  177  21.75 
 3  7140202  Giáo dục Tiểu học  244  234  26.95  240  239  26.9 
 4  7140205  Giáo dục chính trị  20  23  26.65  22  21  26.65 
 5  7140206  Giáo dục thể chất  24  23  26.5  99  98  19.8 `,
      bounding_boxes: [
        {
          id: "bbox_p2_01",
          page_number: 2,
          type: "text",
          coordinates: {
            x: 15.5,
            y: 6.3,
            width: 74.8,
            height: 43.6,
          },
          label: "text",
          confidence: 0.98,
          content_snippet: "Đoạn văn bản quy định",
        },
        {
          id: "bbox_p2_02",
          page_number: 2,
          type: "table",
          coordinates: {
            x: 9.3,
            y: 51.1,
            width: 86.3,
            height: 39.3,
          },
          label: "table",
          confidence: 0.98,
          content_snippet: "Bảng số liệu tuyển sinh",
        },
      ],
      regions: [
        {
          id: "reg_p2_01",
          page_number: 2,
          title: "5 Phương thức tuyển sinh (PT1 - PT5)",
          type: "text",
          confidence: 0.98,
          reading_order: 1,
          details:
            "Chi tiết PT1 thi THPT, PT2 học bạ, PT3 ĐGNL ĐHQG, PT4 ĐGNL ĐHSPHN, PT5 Năng khiếu",
        },
        {
          id: "reg_p2_02",
          page_number: 2,
          title: "4. Các ngành, tổ hợp môn xét tuyển (STT 1-5)",
          type: "table",
          confidence: 0.99,
          reading_order: 2,
          details: "Bảng mã ngành STT 1 Quản lý giáo dục đến STT 5 GD Thể chất",
        },
      ],
    },
    {
      page_number: 3,
      word_count: 256,
      line_count: 14,
      image_url: "/ocr-cache/doc_ts_2026/page_3.jpg",
      markdown_content: `<!-- Trang 3 -->
### 4. Các ngành, tổ hợp môn xét tuyển (tiếp theo)

| STT | Mã xét tuyển | Tên ngành, chương trình xét tuyển | Phương thức tuyển sinh | Số lượng dự kiến | Tổ hợp môn xét tuyển |
| :---: | :---: | :--- | :---: | :---: | :--- |
| 6 | 7140209 | Sư phạm Toán học | 20 | 20 | 26.5 | 101 | 101 | 25.85 |
| 7 | 7140210 | Sư phạm Tin học | 100 | 106 | 22.85 | 112 | 112 | 20.35 |
| 8 | 7140211 | Sư phạm Vật lý | 20 | 19 | 25.75 | 81 | 80 | 24.4 |
| 9 | 7140212 | Sư phạm Hóa học | 0 | 0 | - | 25 | 25 | 25.3 |
| 10 | 7140213 | Sư phạm Sinh học | 20 | 21 | 23.9 | 29 | 29 | 21.2 |
| 11 | 7140217 | Sư phạm Ngữ văn | 30 | 32 | 27.35 | 119 | 119 | 26.85 |
| 12 | 7140218 | Sư phạm Lịch sử | 20 | 23 | 27.45 | 47 | 47 | 27.21 |
| 13 | 7140219 | Sư phạm Địa lý | 20 | 19 | 27.3 | 70 | 70 | 26.74 |
| 14 | 7140231 | Sư phạm Tiếng Anh | 84 | 87 | 25.92 | 199 | 199 | 23.59 |`,
      raw_text: `<!-- Trang 3 --
 4. Các ngành, tổ hợp môn xét tuyển (tiếp theo)

 STT  Mã xét tuyển  Tên ngành, chương trình xét tuyển  Phương thức tuyển sinh  Số lượng dự kiến  Tổ hợp môn xét tuyển 
 :---:  :---:  :---  :---:  :---:  :--- 
 6  7140209  Sư phạm Toán học  20  20  26.5  101  101  25.85 
 7  7140210  Sư phạm Tin học  100  106  22.85  112  112  20.35 
 8  7140211  Sư phạm Vật lý  20  19  25.75  81  80  24.4 
 9  7140212  Sư phạm Hóa học  0  0  -  25  25  25.3 
 10  7140213  Sư phạm Sinh học  20  21  23.9  29  29  21.2 
 11  7140217  Sư phạm Ngữ văn  30  32  27.35  119  119  26.85 
 12  7140218  Sư phạm Lịch sử  20  23  27.45  47  47  27.21 
 13  7140219  Sư phạm Địa lý  20  19  27.3  70  70  26.74 
 14  7140231  Sư phạm Tiếng Anh  84  87  25.92  199  199  23.59 `,
      bounding_boxes: [
        {
          id: "bbox_p3_01",
          page_number: 3,
          type: "table",
          coordinates: {
            x: 9.3,
            y: 5.8,
            width: 86.3,
            height: 82.6,
          },
          label: "table",
          confidence: 0.98,
          content_snippet: "Bảng số liệu tuyển sinh",
        },
      ],
      regions: [
        {
          id: "reg_p3_01",
          page_number: 3,
          title: "Bảng Mã Ngành & Tổ Hợp Môn Xét Tuyển (STT 6-14)",
          type: "table",
          confidence: 0.99,
          reading_order: 1,
          details: "Bảng dữ liệu tuyển sinh TableFormer bóc tách nguyên vẹn các tổ hợp môn",
        },
      ],
    },
    {
      page_number: 4,
      word_count: 254,
      line_count: 14,
      image_url: "/ocr-cache/doc_ts_2026/page_4.jpg",
      markdown_content: `<!-- Trang 4 -->
### 4. Các ngành, tổ hợp môn xét tuyển (tiếp theo)

| STT | Mã xét tuyển | Tên ngành, chương trình xét tuyển | Phương thức tuyển sinh | Số lượng dự kiến | Tổ hợp môn xét tuyển |
| :---: | :---: | :--- | :---: | :---: | :--- |
| 15 | 7140247 | Sư phạm KH tự nhiên | 20 | 17 | 25.65 | 99 | 99 | 22.5 |
| 16 | 7140249 | Sư phạm Lịch sử Địa lý | 27 | 32 | 27.15 | 112 | 112 | 26.4 |
| 17 | 7220201 | Ngôn ngữ Anh | 290 | 288 | 22 | 287 | 285 | 23 |
| 18 | 7220204 | Ngôn ngữ Trung Quốc | 64 | 65 | 23.5 | 66 | 63 | 24.2 |
| 19 | 7229030 | Văn học | 61 | 62 | 23.5 | 56 | 54 | 25.29 |
| 20 | 7310101 | Kinh tế | 114 | 119 | 18 | 113 | 111 | 21.4 |
| 21 | 7310205 | Quản lý nhà nước | 99 | 101 | 23.15 | 77 | 58 | 23.6 |
| 22 | 7310403 | Tâm lý học giáo dục | 73 | 81 | 23 | 71 | 69 | 24.6 |
| 23 | 7310608 | Đông phương học | 128 | 107 | 15 | 107 | 106 | 22.3 |`,
      raw_text: `<!-- Trang 4 --
 4. Các ngành, tổ hợp môn xét tuyển (tiếp theo)

 STT  Mã xét tuyển  Tên ngành, chương trình xét tuyển  Phương thức tuyển sinh  Số lượng dự kiến  Tổ hợp môn xét tuyển 
 :---:  :---:  :---  :---:  :---:  :--- 
 15  7140247  Sư phạm KH tự nhiên  20  17  25.65  99  99  22.5 
 16  7140249  Sư phạm Lịch sử Địa lý  27  32  27.15  112  112  26.4 
 17  7220201  Ngôn ngữ Anh  290  288  22  287  285  23 
 18  7220204  Ngôn ngữ Trung Quốc  64  65  23.5  66  63  24.2 
 19  7229030  Văn học  61  62  23.5  56  54  25.29 
 20  7310101  Kinh tế  114  119  18  113  111  21.4 
 21  7310205  Quản lý nhà nước  99  101  23.15  77  58  23.6 
 22  7310403  Tâm lý học giáo dục  73  81  23  71  69  24.6 
 23  7310608  Đông phương học  128  107  15  107  106  22.3 `,
      bounding_boxes: [
        {
          id: "bbox_p4_01",
          page_number: 4,
          type: "table",
          coordinates: {
            x: 9.3,
            y: 5.9,
            width: 86.3,
            height: 85.3,
          },
          label: "table",
          confidence: 0.98,
          content_snippet: "Bảng số liệu tuyển sinh",
        },
      ],
      regions: [
        {
          id: "reg_p4_01",
          page_number: 4,
          title: "Bảng Mã Ngành & Tổ Hợp Môn Xét Tuyển (STT 15-23)",
          type: "table",
          confidence: 0.99,
          reading_order: 1,
          details: "Bảng dữ liệu tuyển sinh TableFormer bóc tách nguyên vẹn các tổ hợp môn",
        },
      ],
    },
    {
      page_number: 5,
      word_count: 204,
      line_count: 12,
      image_url: "/ocr-cache/doc_ts_2026/page_5.jpg",
      markdown_content: `<!-- Trang 5 -->
### 4. Các ngành, tổ hợp môn xét tuyển (tiếp theo)

| STT | Mã xét tuyển | Tên ngành, chương trình xét tuyển | Phương thức tuyển sinh | Số lượng dự kiến | Tổ hợp môn xét tuyển |
| :---: | :---: | :--- | :---: | :---: | :--- |
| 24 | 7310630 | Việt Nam học | 64 | 69 | 18 | 61 | 57 | 23.5 |
| 25 | 7340101 | Quản trị kinh doanh | 266 | 264 | 17 | 250 | 249 | 21.7 |
| 26 | 7340201 | Tài chính – Ngân hàng | 86 | 92 | 20.25 | 102 | 87 | 22.5 |
| 27 | 7340301 | Kế toán | 262 | 258 | 17.75 | 238 | 236 | 20.3 |
| 28 | 7340301ACCA | Kế toán ACCA | 30 | 29 | 18 | 30 | 33 | 19.2 |
| 29 | 7340302 | Kiểm toán | 54 | 56 | 18.75 | 50 | 50 | 21.8 |
| 30 | 7380101 | Luật | 200 | 188 | 23.65 | 170 | 158 | 23.58 |`,
      raw_text: `<!-- Trang 5 --
 4. Các ngành, tổ hợp môn xét tuyển (tiếp theo)

 STT  Mã xét tuyển  Tên ngành, chương trình xét tuyển  Phương thức tuyển sinh  Số lượng dự kiến  Tổ hợp môn xét tuyển 
 :---:  :---:  :---  :---:  :---:  :--- 
 24  7310630  Việt Nam học  64  69  18  61  57  23.5 
 25  7340101  Quản trị kinh doanh  266  264  17  250  249  21.7 
 26  7340201  Tài chính – Ngân hàng  86  92  20.25  102  87  22.5 
 27  7340301  Kế toán  262  258  17.75  238  236  20.3 
 28  7340301ACCA  Kế toán ACCA  30  29  18  30  33  19.2 
 29  7340302  Kiểm toán  54  56  18.75  50  50  21.8 
 30  7380101  Luật  200  188  23.65  170  158  23.58 `,
      bounding_boxes: [
        {
          id: "bbox_p5_01",
          page_number: 5,
          type: "table",
          coordinates: {
            x: 9.3,
            y: 5.9,
            width: 86.3,
            height: 84.1,
          },
          label: "table",
          confidence: 0.98,
          content_snippet: "Bảng số liệu tuyển sinh",
        },
      ],
      regions: [
        {
          id: "reg_p5_01",
          page_number: 5,
          title: "Bảng Mã Ngành & Tổ Hợp Môn Xét Tuyển (STT 24-30)",
          type: "table",
          confidence: 0.99,
          reading_order: 1,
          details: "Bảng dữ liệu tuyển sinh TableFormer bóc tách nguyên vẹn các tổ hợp môn",
        },
      ],
    },
    {
      page_number: 6,
      word_count: 258,
      line_count: 14,
      image_url: "/ocr-cache/doc_ts_2026/page_6.jpg",
      markdown_content: `<!-- Trang 6 -->
### 4. Các ngành, tổ hợp môn xét tuyển (tiếp theo)

| STT | Mã xét tuyển | Tên ngành, chương trình xét tuyển | Phương thức tuyển sinh | Số lượng dự kiến | Tổ hợp môn xét tuyển |
| :---: | :---: | :--- | :---: | :---: | :--- |
| 31 | 7440112 | Hóa học | 50 | 32 | 15 | 49 | 50 | 20.5 |
| 32 | 7460108 | Khoa học dữ liệu | 45 | 17 | 15 | 40 | 41 | 17.1 |
| 33 | 7460112 | Toán ứng dụng | 55 | 47 | 15 | 60 | 60 | 19.5 |
| 34 | 7480103 | Kỹ thuật phần mềm | 61 | 50 | 15 | 61 | 58 | 19.5 |
| 35 | 7480107 | Trí tuệ nhân tạo | 52 | 18 | 15 | 55 | 50 | 20 |
| 36 | 7480201 | Công nghệ thông tin | 304 | 349 | 16.5 | 172 | 171 | 21.5 |
| 37 | 7510205 | Công nghệ kỹ thuật ô tô | 186 | 169 | 16 | 122 | 111 | 22.2 |
| 38 | 7510401 | Công nghệ KT hoá học | 50 | 19 | 15 | 41 | 47 | 20.5 |
| 39 | 7510605 | Logistics và QL chuỗi cung ứng | 170 | 218 | 21 | 184 | 164 | 23.6 |`,
      raw_text: `<!-- Trang 6 --
 4. Các ngành, tổ hợp môn xét tuyển (tiếp theo)

 STT  Mã xét tuyển  Tên ngành, chương trình xét tuyển  Phương thức tuyển sinh  Số lượng dự kiến  Tổ hợp môn xét tuyển 
 :---:  :---:  :---  :---:  :---:  :--- 
 31  7440112  Hóa học  50  32  15  49  50  20.5 
 32  7460108  Khoa học dữ liệu  45  17  15  40  41  17.1 
 33  7460112  Toán ứng dụng  55  47  15  60  60  19.5 
 34  7480103  Kỹ thuật phần mềm  61  50  15  61  58  19.5 
 35  7480107  Trí tuệ nhân tạo  52  18  15  55  50  20 
 36  7480201  Công nghệ thông tin  304  349  16.5  172  171  21.5 
 37  7510205  Công nghệ kỹ thuật ô tô  186  169  16  122  111  22.2 
 38  7510401  Công nghệ KT hoá học  50  19  15  41  47  20.5 
 39  7510605  Logistics và QL chuỗi cung ứng  170  218  21  184  164  23.6 `,
      bounding_boxes: [
        {
          id: "bbox_p6_01",
          page_number: 6,
          type: "table",
          coordinates: {
            x: 9.3,
            y: 5.9,
            width: 86.3,
            height: 85.5,
          },
          label: "table",
          confidence: 0.98,
          content_snippet: "Bảng số liệu tuyển sinh",
        },
      ],
      regions: [
        {
          id: "reg_p6_01",
          page_number: 6,
          title: "Bảng Mã Ngành & Tổ Hợp Môn Xét Tuyển (STT 31-39)",
          type: "table",
          confidence: 0.99,
          reading_order: 1,
          details: "Bảng dữ liệu tuyển sinh TableFormer bóc tách nguyên vẹn các tổ hợp môn",
        },
      ],
    },
    {
      page_number: 7,
      word_count: 262,
      line_count: 14,
      image_url: "/ocr-cache/doc_ts_2026/page_7.jpg",
      markdown_content: `<!-- Trang 7 -->
### 4. Các ngành, tổ hợp môn xét tuyển (tiếp theo)

| STT | Mã xét tuyển | Tên ngành, chương trình xét tuyển | Phương thức tuyển sinh | Số lượng dự kiến | Tổ hợp môn xét tuyển |
| :---: | :---: | :--- | :---: | :---: | :--- |
| 40 | 7520116 | Kỹ thuật cơ khí động lực | 0 | 0 | 0 | 33 | 38 | 20.14 |
| 41 | 7520201 | Kỹ thuật điện | 113 | 143 | 16 | 144 | 137 | 20.65 |
| 42 | 7520207 | Kỹ thuật điện tử - viễn thông | 89 | 61 | 15 | 89 | 90 | 20.77 |
| 43 | 7520216 | Kỹ thuật điều khiển và Tự động hóa | 74 | 67 | 15 | 85 | 76 | 21.02 |
| 44 | 7520401 | Vật lý kỹ thuật | 0 | 0 | 0 | 57 | 56 | 18.25 |
| 45 | 7540101 | Công nghệ thực phẩm | 170 | 142 | 15 | 148 | 137 | 20.9 |
| 46 | 7580201 | Kỹ thuật xây dựng | 100 | 96 | 15 | 97 | 99 | 20.15 |
| 47 | 7620109 | Nông học | 50 | 29 | 15 | 44 | 39 | 15 |
| 48 | 7760101 | Công tác xã hội | 96 | 77 | 20.25 | 65 | 48 | 23.7 |`,
      raw_text: `<!-- Trang 7 --
 4. Các ngành, tổ hợp môn xét tuyển (tiếp theo)

 STT  Mã xét tuyển  Tên ngành, chương trình xét tuyển  Phương thức tuyển sinh  Số lượng dự kiến  Tổ hợp môn xét tuyển 
 :---:  :---:  :---  :---:  :---:  :--- 
 40  7520116  Kỹ thuật cơ khí động lực  0  0  0  33  38  20.14 
 41  7520201  Kỹ thuật điện  113  143  16  144  137  20.65 
 42  7520207  Kỹ thuật điện tử - viễn thông  89  61  15  89  90  20.77 
 43  7520216  Kỹ thuật điều khiển và Tự động hóa  74  67  15  85  76  21.02 
 44  7520401  Vật lý kỹ thuật  0  0  0  57  56  18.25 
 45  7540101  Công nghệ thực phẩm  170  142  15  148  137  20.9 
 46  7580201  Kỹ thuật xây dựng  100  96  15  97  99  20.15 
 47  7620109  Nông học  50  29  15  44  39  15 
 48  7760101  Công tác xã hội  96  77  20.25  65  48  23.7 `,
      bounding_boxes: [
        {
          id: "bbox_p7_01",
          page_number: 7,
          type: "table",
          coordinates: {
            x: 9.3,
            y: 5.9,
            width: 86.3,
            height: 84.5,
          },
          label: "table",
          confidence: 0.98,
          content_snippet: "Bảng số liệu tuyển sinh",
        },
      ],
      regions: [
        {
          id: "reg_p7_01",
          page_number: 7,
          title: "Bảng Mã Ngành & Tổ Hợp Môn Xét Tuyển (STT 40-48)",
          type: "table",
          confidence: 0.99,
          reading_order: 1,
          details: "Bảng dữ liệu tuyển sinh TableFormer bóc tách nguyên vẹn các tổ hợp môn",
        },
      ],
    },
    {
      page_number: 8,
      word_count: 284,
      line_count: 14,
      image_url: "/ocr-cache/doc_ts_2026/page_8.jpg",
      markdown_content: `<!-- Trang 8 -->
### 4. Các ngành, tổ hợp môn xét tuyển (tiếp theo)

| STT | Mã xét tuyển | Tên ngành, chương trình xét tuyển | Phương thức tuyển sinh | Số lượng dự kiến | Tổ hợp môn xét tuyển |
| :---: | :---: | :--- | :---: | :---: | :--- |
| 49 | 7810103 | Quản trị dịch vụ du lịch và lữ hành | 131 | 154 | 19.85 | 146 | 122 | 22.25 |
| 50 | 7810201 | Quản trị khách sạn | 167 | 128 | 18.35 | 113 | 90 | 22.65 |
| 51 | 7850101 | Quản lý tài nguyên và môi trường | 100 | 84 | 15 | 102 | 101 | 20.75 |
| 52 | 7850103 | Quản lý đất đai | 100 | 105 | 15 | 119 | 115 | 17.9 |
| 53 | 7850103 | Quản lý đất đai | 1,2,3,4 | - | (Địa, Văn, Giáo dục KT và PL)<br>(Địa, Toán, Giáo dục KT và PL)<br>(Địa, Toán, Văn)<br>(Địa, Toán, Sinh)<br>(Địa, Văn, Anh)<br>(Địa, Toán, Lý)<br>(Địa, Toán, Anh)<br>(Địa, Văn, Sinh)<br>(Địa, Toán, Hóa) |

### 5. Các thông tin cần thiết khác để thí sinh dự tuyển
**a. Điều kiện phụ sử dụng trong xét tuyển:**
Trường hợp nhiều thí sinh có cùng điểm xét ở cuối danh sách, thứ tự xét ưu tiên đối với các thí sinh có điểm cộng thấp hơn; trường hợp nhiều thí sinh có cùng điểm xét ở cuối danh sách và có điểm cộng bằng nhau, thứ tự xét ưu tiên đối với các thí sinh có thứ tự ưu tiên nguyện vọng cao hơn;`,
      raw_text: `<!-- Trang 8 --
 4. Các ngành, tổ hợp môn xét tuyển (tiếp theo)

 STT  Mã xét tuyển  Tên ngành, chương trình xét tuyển  Phương thức tuyển sinh  Số lượng dự kiến  Tổ hợp môn xét tuyển 
 :---:  :---:  :---  :---:  :---:  :--- 
 49  7810103  Quản trị dịch vụ du lịch và lữ hành  131  154  19.85  146  122  22.25 
 50  7810201  Quản trị khách sạn  167  128  18.35  113  90  22.65 
 51  7850101  Quản lý tài nguyên và môi trường  100  84  15  102  101  20.75 
 52  7850103  Quản lý đất đai  100  105  15  119  115  17.9 
 53  7850103  Quản lý đất đai  1,2,3,4  -  (Địa, Văn, Giáo dục KT và PL)<br(Địa, Toán, Giáo dục KT và PL)<br(Địa, Toán, Văn)<br(Địa, Toán, Sinh)<br(Địa, Văn, Anh)<br(Địa, Toán, Lý)<br(Địa, Toán, Anh)<br(Địa, Văn, Sinh)<br(Địa, Toán, Hóa) 

 5. Các thông tin cần thiết khác để thí sinh dự tuyển
a. Điều kiện phụ sử dụng trong xét tuyển:
Trường hợp nhiều thí sinh có cùng điểm xét ở cuối danh sách, thứ tự xét ưu tiên đối với các thí sinh có điểm cộng thấp hơn; trường hợp nhiều thí sinh có cùng điểm xét ở cuối danh sách và có điểm cộng bằng nhau, thứ tự xét ưu tiên đối với các thí sinh có thứ tự ưu tiên nguyện vọng cao hơn;`,
      bounding_boxes: [
        {
          id: "bbox_p8_01",
          page_number: 8,
          type: "table",
          coordinates: {
            x: 9.3,
            y: 5.9,
            width: 86.3,
            height: 77.7,
          },
          label: "table",
          confidence: 0.98,
          content_snippet: "Bảng số liệu tuyển sinh",
        },
        {
          id: "bbox_p8_02",
          page_number: 8,
          type: "text",
          coordinates: {
            x: 19.1,
            y: 84.3,
            width: 50.1,
            height: 4.4,
          },
          label: "text",
          confidence: 0.98,
          content_snippet: "Đoạn văn bản quy định",
        },
      ],
      regions: [
        {
          id: "reg_p8_01",
          page_number: 8,
          title: "Bảng Mã Ngành & Tổ Hợp Môn Xét Tuyển (STT 49-53)",
          type: "table",
          confidence: 0.99,
          reading_order: 1,
          details:
            "5 ngành cuối cùng: Công tác xã hội, QTDV du lịch, QT khách sạn, Quản lý TN&MT, Quản lý đất đai",
        },
        {
          id: "reg_p8_02",
          page_number: 8,
          title: "5. Các thông tin cần thiết khác (Điều kiện phụ)",
          type: "text",
          confidence: 0.97,
          reading_order: 2,
          details: "Quy tắc xét ưu tiên điểm cộng và thứ tự nguyện vọng",
        },
      ],
    },
    {
      page_number: 9,
      word_count: 341,
      line_count: 24,
      image_url: "/ocr-cache/doc_ts_2026/page_9.jpg",
      markdown_content: `<!-- Trang 9 -->
**b. Điểm cộng**: xem chi tiết tại Mục 7;

**c. Sử dụng chứng chỉ VSTEP, IELTS (còn hiệu lực) thay cho điểm môn Tiếng Anh trong tổ hợp môn xét tuyển, khi xét tuyển theo Phương thức 1 và phương thức 2, được quy đổi như sau:**

| Điểm IELTS | Điểm quy đổi | Điểm VSTEP | Điểm quy đổi |
| :---: | :---: | :---: | :---: |
| 5.0 | 8.0 | 4.0 | 8.0 |
| 5.5 | 8.5 | 5.0 | 8.5 |
| 6.0 | 9.0 | 6.0 | 9.0 |
| 6.5 | 9.5 | 7.0 | 9.5 |
| 7.0 trở lên | 10.0 | 8.0 trở lên | 10.0 |

*Thí sinh nộp chứng chỉ tại các điểm tiếp nhận để nhập lên cơ sở dữ liệu tuyển sinh của Bộ GD&ĐT.*

**d. Ngưỡng đầu vào các ngành**: các phương thức thực hiện theo các quy định tại Quy chế tuyển sinh đại học của Bộ Giáo dục và Đào tạo. Riêng đối với ngành Giáo dục Thể chất, thí sinh xét tuyển phải không bị dị tật cột sống, tay chân, mắt, phát âm và các dị tật khác; chiều cao tối thiểu là 1,65m, nặng 45 kg đối với nam và 1,55m, nặng 40 kg đối với nữ.

### 6. Tổ chức tuyển sinh
**Đợt 1:**
- **a)** Thí sinh nộp hồ sơ xét tuyển thẳng, ưu tiên xét tuyển từ ngày 20/5/2026 đến ngày 20/6/2026.
- **b)** Thi năng khiếu Giáo dục mầm non, Giáo dục thể chất: thi vào các ngày 19, 20, 21/6/2026. Thí sinh đăng ký thi năng khiếu tại https://tsd.qnu.edu.vn từ ngày 20/5/2026 đến 15/6/2026.
- **c) Xét tuyển đợt 1:**
  Tất cả thí sinh, tất cả các phương thức phải đăng ký xét tuyển trên hệ thống của Bộ từ ngày 02/7/2026 đến ngày 14/7/2026.
  Công bố ngưỡng bảo đảm chất lượng đầu vào và quy tắc quy đổi điểm giữa các phương thức: theo quy định của Bộ.`,
      raw_text: `<!-- Trang 9 --
b. Điểm cộng: xem chi tiết tại Mục 7;

c. Sử dụng chứng chỉ VSTEP, IELTS (còn hiệu lực) thay cho điểm môn Tiếng Anh trong tổ hợp môn xét tuyển, khi xét tuyển theo Phương thức 1 và phương thức 2, được quy đổi như sau:

 Điểm IELTS  Điểm quy đổi  Điểm VSTEP  Điểm quy đổi 
 :---:  :---:  :---:  :---: 
 5.0  8.0  4.0  8.0 
 5.5  8.5  5.0  8.5 
 6.0  9.0  6.0  9.0 
 6.5  9.5  7.0  9.5 
 7.0 trở lên  10.0  8.0 trở lên  10.0 

Thí sinh nộp chứng chỉ tại các điểm tiếp nhận để nhập lên cơ sở dữ liệu tuyển sinh của Bộ GD&ĐT.

d. Ngưỡng đầu vào các ngành: các phương thức thực hiện theo các quy định tại Quy chế tuyển sinh đại học của Bộ Giáo dục và Đào tạo. Riêng đối với ngành Giáo dục Thể chất, thí sinh xét tuyển phải không bị dị tật cột sống, tay chân, mắt, phát âm và các dị tật khác; chiều cao tối thiểu là 1,65m, nặng 45 kg đối với nam và 1,55m, nặng 40 kg đối với nữ.

 6. Tổ chức tuyển sinh
Đợt 1:
- a) Thí sinh nộp hồ sơ xét tuyển thẳng, ưu tiên xét tuyển từ ngày 20/5/2026 đến ngày 20/6/2026.
- b) Thi năng khiếu Giáo dục mầm non, Giáo dục thể chất: thi vào các ngày 19, 20, 21/6/2026. Thí sinh đăng ký thi năng khiếu tại https://tsd.qnu.edu.vn từ ngày 20/5/2026 đến 15/6/2026.
- c) Xét tuyển đợt 1:
  Tất cả thí sinh, tất cả các phương thức phải đăng ký xét tuyển trên hệ thống của Bộ từ ngày 02/7/2026 đến ngày 14/7/2026.
  Công bố ngưỡng bảo đảm chất lượng đầu vào và quy tắc quy đổi điểm giữa các phương thức: theo quy định của Bộ.`,
      bounding_boxes: [
        {
          id: "bbox_p9_01",
          page_number: 9,
          type: "text",
          coordinates: {
            x: 14.3,
            y: 6.6,
            width: 76.0,
            height: 18.0,
          },
          label: "text",
          confidence: 0.98,
          content_snippet: "Đoạn văn bản quy định",
        },
        {
          id: "bbox_p9_02",
          page_number: 9,
          type: "table",
          coordinates: {
            x: 18.7,
            y: 28.1,
            width: 67.5,
            height: 17.9,
          },
          label: "table",
          confidence: 0.98,
          content_snippet: "Bảng số liệu tuyển sinh",
        },
        {
          id: "bbox_p9_03",
          page_number: 9,
          type: "text",
          coordinates: {
            x: 14.3,
            y: 47.0,
            width: 76.0,
            height: 43.3,
          },
          label: "text",
          confidence: 0.98,
          content_snippet: "Đoạn văn bản quy định",
        },
      ],
      regions: [
        {
          id: "reg_p9_01",
          page_number: 9,
          title: "Bảng Quy đổi Điểm IELTS / VSTEP",
          type: "table",
          confidence: 0.99,
          reading_order: 1,
          details: "Bảng thang điểm quy đổi môn Tiếng Anh: IELTS 5.0-7.0+, VSTEP 4.0-8.0+",
        },
        {
          id: "reg_p9_02",
          page_number: 9,
          title: "Ngưỡng đầu vào & Tiêu chuẩn sức khỏe GDTC",
          type: "text",
          confidence: 0.98,
          reading_order: 2,
          details: "Quy định chiều cao, cân nặng và không dị tật cho ngành GDTC",
        },
        {
          id: "reg_p9_03",
          page_number: 9,
          title: "6. Kế hoạch Tổ chức Tuyển sinh Đợt 1",
          type: "text",
          confidence: 0.98,
          reading_order: 3,
          details: "Lịch nộp hồ sơ xét tuyển thẳng (20/5 - 20/6) và thi năng khiếu (19-21/6)",
        },
      ],
    },
    {
      page_number: 10,
      word_count: 298,
      line_count: 19,
      image_url: "/ocr-cache/doc_ts_2026/page_10.jpg",
      markdown_content: `<!-- Trang 10 -->
Xét tuyển theo kế hoạch của Bộ GDĐT: **04/8/2026 – 10/8/2026**.

**Đợt 2:**  
Xét tuyển các ngành còn chỉ tiêu sau khi thí sinh đăng ký nhập học đợt 1, thông báo từ ngày **22/8/2026**.

### 7. Chính sách ưu tiên
- **Xét tuyển thẳng**: theo Quy chế tuyển sinh của Bộ Giáo dục và Đào tạo vào các ngành phù hợp theo **Phụ lục 1**.
- **Ưu tiên xét tuyển:**
  - Thí sinh đoạt giải trong kỳ thi chọn học sinh giỏi quốc gia, Cuộc thi khoa học, kỹ thuật cấp quốc gia: giải Nhất cộng 3 điểm, giải Nhì cộng 2 điểm, giải Ba cộng 1 điểm, giải Khuyến khích hoặc giải Tư cộng 0,5 điểm vào tổng điểm 3 môn xét tuyển.
  - Thí sinh tham gia đội tuyển quốc gia thi đấu tại các giải quốc tế chính thức (Thế giới, Olympic, ASIAD, SEA Games) được cộng 3 điểm vào ngành Giáo dục thể chất.
  - Thí sinh đoạt huy chương vàng, bạc, đồng cấp quốc gia và kiện tướng quốc gia được cộng 1 điểm vào ngành Giáo dục thể chất.

### 8. Lệ phí xét tuyển, thi tuyển, học phí
- **Lệ phí**: Thi năng khiếu GDMN, GDTC: 300.000 đ/thí sinh. Lệ phí xét tuyển: theo quy định của Bộ GDĐT.
- **Học phí:**
  - Các chương trình đào tạo đại trà theo Nghị định 238/2025/NĐ-CP ngày 03/9/2025;
  - Chương trình đào tạo Kế toán (ACCA) và các chương trình đào tạo giảng dạy bằng tiếng Anh (CNTT, Kỹ thuật điện, Tài chính – Ngân hàng) xác định trên cơ sở định mức kinh tế - kỹ thuật;
  - Học phí toàn khóa dự kiến cử nhân đại trà: **83 - 97 triệu đồng** (khóa học 4 năm).`,
      raw_text: `<!-- Trang 10 --
Xét tuyển theo kế hoạch của Bộ GDĐT: 04/8/2026 – 10/8/2026.

Đợt 2:  
Xét tuyển các ngành còn chỉ tiêu sau khi thí sinh đăng ký nhập học đợt 1, thông báo từ ngày 22/8/2026.

 7. Chính sách ưu tiên
- Xét tuyển thẳng: theo Quy chế tuyển sinh của Bộ Giáo dục và Đào tạo vào các ngành phù hợp theo Phụ lục 1.
- Ưu tiên xét tuyển:
  - Thí sinh đoạt giải trong kỳ thi chọn học sinh giỏi quốc gia, Cuộc thi khoa học, kỹ thuật cấp quốc gia: giải Nhất cộng 3 điểm, giải Nhì cộng 2 điểm, giải Ba cộng 1 điểm, giải Khuyến khích hoặc giải Tư cộng 0,5 điểm vào tổng điểm 3 môn xét tuyển.
  - Thí sinh tham gia đội tuyển quốc gia thi đấu tại các giải quốc tế chính thức (Thế giới, Olympic, ASIAD, SEA Games) được cộng 3 điểm vào ngành Giáo dục thể chất.
  - Thí sinh đoạt huy chương vàng, bạc, đồng cấp quốc gia và kiện tướng quốc gia được cộng 1 điểm vào ngành Giáo dục thể chất.

 8. Lệ phí xét tuyển, thi tuyển, học phí
- Lệ phí: Thi năng khiếu GDMN, GDTC: 300.000 đ/thí sinh. Lệ phí xét tuyển: theo quy định của Bộ GDĐT.
- Học phí:
  - Các chương trình đào tạo đại trà theo Nghị định 238/2025/NĐ-CP ngày 03/9/2025;
  - Chương trình đào tạo Kế toán (ACCA) và các chương trình đào tạo giảng dạy bằng tiếng Anh (CNTT, Kỹ thuật điện, Tài chính – Ngân hàng) xác định trên cơ sở định mức kinh tế - kỹ thuật;
  - Học phí toàn khóa dự kiến cử nhân đại trà: 83 - 97 triệu đồng (khóa học 4 năm).`,
      bounding_boxes: [
        {
          id: "bbox_p10_01",
          page_number: 10,
          type: "text",
          coordinates: {
            x: 14.3,
            y: 6.3,
            width: 76.0,
            height: 83.3,
          },
          label: "text",
          confidence: 0.98,
          content_snippet: "Đoạn văn bản quy định",
        },
      ],
      regions: [
        {
          id: "reg_p10_01",
          page_number: 10,
          title: "7. Chính sách Ưu tiên & Xét tuyển thẳng",
          type: "text",
          confidence: 0.98,
          reading_order: 1,
          details: "Mức điểm cộng ưu tiên giải quốc gia (0.5 - 3.0 điểm) và vận động viên",
        },
        {
          id: "reg_p10_02",
          page_number: 10,
          title: "8. Lệ phí Xét tuyển & Khung Học phí",
          type: "text",
          confidence: 0.98,
          reading_order: 2,
          details: "Lệ phí năng khiếu 300.000đ; Học phí đại trà 83-97 triệu/4 năm; Kế toán ACCA",
        },
      ],
    },
    {
      page_number: 11,
      word_count: 824,
      line_count: 43,
      image_url: "/ocr-cache/doc_ts_2026/page_11.jpg",
      markdown_content: `<!-- Trang 11 -->
- Các chương trình đào tạo kỹ sư đại trà: **112,3 triệu đồng** (khóa học 4,5 năm).
- Các chương trình đào tạo giảng dạy bằng tiếng Anh, Kế toán (ACCA) dự kiến bằng 1,5 so với chương trình đại trà.

### 9. Cam kết với thí sinh
Hội đồng tuyển sinh sẽ giải quyết theo yêu cầu của thí sinh trên cơ sở kiểm tra trách nhiệm của các bên liên quan trong quá trình xét tuyển.

### 10. Các nội dung khác: Không.

### 11. Thông tin về tuyển sinh của 2 năm gần nhất
| STT | Mã ngành | Tên ngành | Chỉ tiêu (2024) | Trúng tuyển (2024) | Điểm chuẩn (2024) | Chỉ tiêu (2025) | Trúng tuyển (2025) | Điểm chuẩn (2025) |
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
| 17 | 7220201 | Ngôn ngữ Anh | 290 | 288 | 22 | 287 | 285 | 23 |
| 18 | 7220204 | Ngôn ngữ Trung Quốc | 64 | 65 | 23.5 | 66 | 63 | 24.2 |
| 19 | 7229030 | Văn học | 61 | 62 | 23.5 | 56 | 54 | 25.29 |
| 20 | 7310101 | Kinh tế | 114 | 119 | 18 | 113 | 111 | 21.4 |
| 21 | 7310205 | Quản lý nhà nước | 99 | 101 | 23.15 | 77 | 58 | 23.6 |
| 22 | 7310403 | Tâm lý học giáo dục | 73 | 81 | 23 | 71 | 69 | 24.6 |
| 23 | 7310608 | Đông phương học | 128 | 107 | 15 | 107 | 106 | 22.3 |
| 24 | 7310630 | Việt Nam học | 64 | 69 | 18 | 61 | 57 | 23.5 |
| 25 | 7340101 | Quản trị kinh doanh | 266 | 264 | 17 | 250 | 249 | 21.7 |
| 26 | 7340201 | Tài chính – Ngân hàng | 86 | 92 | 20.25 | 102 | 87 | 22.5 |
| 27 | 7340301 | Kế toán | 262 | 258 | 17.75 | 238 | 236 | 20.3 |
| 29 | 7340302 | Kiểm toán | 54 | 56 | 18.75 | 50 | 50 | 21.8 |
| 30 | 7380101 | Luật | 200 | 188 | 23.65 | 170 | 158 | 23.58 |
| 31 | 7440112 | Hóa học | 50 | 32 | 15 | 49 | 50 | 20.5 |
| 32 | 7460108 | Khoa học dữ liệu | 45 | 17 | 15 | 40 | 41 | 17.1 |`,
      raw_text: `<!-- Trang 11 --
- Các chương trình đào tạo kỹ sư đại trà: 112,3 triệu đồng (khóa học 4,5 năm).
- Các chương trình đào tạo giảng dạy bằng tiếng Anh, Kế toán (ACCA) dự kiến bằng 1,5 so với chương trình đại trà.

 9. Cam kết với thí sinh
Hội đồng tuyển sinh sẽ giải quyết theo yêu cầu của thí sinh trên cơ sở kiểm tra trách nhiệm của các bên liên quan trong quá trình xét tuyển.

 10. Các nội dung khác: Không.

 11. Thông tin về tuyển sinh của 2 năm gần nhất
 STT  Mã ngành  Tên ngành  Chỉ tiêu (2024)  Trúng tuyển (2024)  Điểm chuẩn (2024)  Chỉ tiêu (2025)  Trúng tuyển (2025)  Điểm chuẩn (2025) 
 :---:  :---:  :---  :---:  :---:  :---:  :---:  :---:  :---: 
 1  7140114  Quản lý Giáo dục  47  50  22.5  50  41  25.1 
 2  7140201  Giáo dục mầm non  126  118  23.1  177  177  21.75 
 3  7140202  Giáo dục Tiểu học  244  234  26.95  240  239  26.9 
 4  7140205  Giáo dục chính trị  20  23  26.65  22  21  26.65 
 5  7140206  Giáo dục thể chất  24  23  26.5  99  98  19.8 
 6  7140209  Sư phạm Toán học  20  20  26.5  101  101  25.85 
 7  7140210  Sư phạm Tin học  100  106  22.85  112  112  20.35 
 8  7140211  Sư phạm Vật lý  20  19  25.75  81  80  24.4 
 9  7140212  Sư phạm Hóa học  0  0  -  25  25  25.3 
 10  7140213  Sư phạm Sinh học  20  21  23.9  29  29  21.2 
 11  7140217  Sư phạm Ngữ văn  30  32  27.35  119  119  26.85 
 12  7140218  Sư phạm Lịch sử  20  23  27.45  47  47  27.21 
 13  7140219  Sư phạm Địa lý  20  19  27.3  70  70  26.74 
 14  7140231  Sư phạm Tiếng Anh  84  87  25.92  199  199  23.59 
 15  7140247  Sư phạm KH tự nhiên  20  17  25.65  99  99  22.5 
 16  7140249  Sư phạm Lịch sử Địa lý  27  32  27.15  112  112  26.4 
 17  7220201  Ngôn ngữ Anh  290  288  22  287  285  23 
 18  7220204  Ngôn ngữ Trung Quốc  64  65  23.5  66  63  24.2 
 19  7229030  Văn học  61  62  23.5  56  54  25.29 
 20  7310101  Kinh tế  114  119  18  113  111  21.4 
 21  7310205  Quản lý nhà nước  99  101  23.15  77  58  23.6 
 22  7310403  Tâm lý học giáo dục  73  81  23  71  69  24.6 
 23  7310608  Đông phương học  128  107  15  107  106  22.3 
 24  7310630  Việt Nam học  64  69  18  61  57  23.5 
 25  7340101  Quản trị kinh doanh  266  264  17  250  249  21.7 
 26  7340201  Tài chính – Ngân hàng  86  92  20.25  102  87  22.5 
 27  7340301  Kế toán  262  258  17.75  238  236  20.3 
 29  7340302  Kiểm toán  54  56  18.75  50  50  21.8 
 30  7380101  Luật  200  188  23.65  170  158  23.58 
 31  7440112  Hóa học  50  32  15  49  50  20.5 
 32  7460108  Khoa học dữ liệu  45  17  15  40  41  17.1 `,
      bounding_boxes: [
        {
          id: "bbox_p11_01",
          page_number: 11,
          type: "text",
          coordinates: {
            x: 14.3,
            y: 6.3,
            width: 76.0,
            height: 17.6,
          },
          label: "text",
          confidence: 0.98,
          content_snippet: "Đoạn văn bản quy định",
        },
        {
          id: "bbox_p11_02",
          page_number: 11,
          type: "table",
          coordinates: {
            x: 14.4,
            y: 24.2,
            width: 85.6,
            height: 66.5,
          },
          label: "table",
          confidence: 0.98,
          content_snippet: "Bảng số liệu tuyển sinh",
        },
      ],
      regions: [
        {
          id: "reg_p11_01",
          page_number: 11,
          title: "Học phí Kỹ sư & Cam kết Đào tạo",
          type: "text",
          confidence: 0.97,
          reading_order: 1,
          details: "Kỹ sư 112.3 triệu/4.5 năm; Cam kết Hội đồng tuyển sinh",
        },
        {
          id: "reg_p11_02",
          page_number: 11,
          title: "11. Bảng Điểm chuẩn & Chỉ tiêu Tuyển sinh 2 năm (STT 1-32)",
          type: "table",
          confidence: 0.99,
          reading_order: 2,
          details: "Chỉ tiêu, số trúng tuyển và điểm chuẩn năm 2024 và năm 2025",
        },
      ],
    },
    {
      page_number: 12,
      word_count: 565,
      line_count: 40,
      image_url: "/ocr-cache/doc_ts_2026/page_12.jpg",
      markdown_content: `<!-- Trang 12 -->
### 11. Thông tin về tuyển sinh của 2 năm gần nhất (tiếp theo)
| STT | Mã ngành | Tên ngành | Chỉ tiêu (2024) | Trúng tuyển (2024) | Điểm chuẩn (2024) | Chỉ tiêu (2025) | Trúng tuyển (2025) | Điểm chuẩn (2025) |
| :---: | :---: | :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| 33 | 7460112 | Toán ứng dụng | 55 | 47 | 15 | 60 | 60 | 19.5 |
| 34 | 7480103 | Kỹ thuật phần mềm | 61 | 50 | 15 | 61 | 58 | 19.5 |
| 35 | 7480107 | Trí tuệ nhân tạo | 52 | 18 | 15 | 55 | 50 | 20 |
| 36 | 7480201 | Công nghệ thông tin | 304 | 349 | 16.5 | 172 | 171 | 21.5 |
| 37 | 7510205 | Công nghệ kỹ thuật ô tô | 186 | 169 | 16 | 122 | 111 | 22.2 |
| 38 | 7510401 | Công nghệ KT hoá học | 50 | 19 | 15 | 41 | 47 | 20.5 |
| 39 | 7510605 | Logistics và QL chuỗi cung ứng | 170 | 218 | 21 | 184 | 164 | 23.6 |
| 40 | 7520116 | Kỹ thuật cơ khí động lực | 0 | 0 | 0 | 33 | 38 | 20.14 |
| 41 | 7520201 | Kỹ thuật điện | 113 | 143 | 16 | 144 | 137 | 20.65 |
| 42 | 7520207 | Kỹ thuật điện tử - viễn thông | 89 | 61 | 15 | 89 | 90 | 20.77 |
| 43 | 7520216 | Kỹ thuật điều khiển và Tự động hóa | 74 | 67 | 15 | 85 | 76 | 21.02 |
| 44 | 7520401 | Vật lý kỹ thuật | 0 | 0 | 0 | 57 | 56 | 18.25 |
| 45 | 7540101 | Công nghệ thực phẩm | 170 | 142 | 15 | 148 | 137 | 20.9 |
| 46 | 7580201 | Kỹ thuật xây dựng | 100 | 96 | 15 | 97 | 99 | 20.15 |
| 47 | 7620109 | Nông học | 50 | 29 | 15 | 44 | 39 | 15 |
| 48 | 7760101 | Công tác xã hội | 96 | 77 | 20.25 | 65 | 48 | 23.7 |
| 49 | 7810103 | Quản trị dịch vụ du lịch và lữ hành | 131 | 154 | 19.85 | 146 | 122 | 22.25 |
| 50 | 7810201 | Quản trị khách sạn | 167 | 128 | 18.35 | 113 | 90 | 22.65 |
| 51 | 7850101 | Quản lý tài nguyên và môi trường | 100 | 84 | 15 | 102 | 101 | 20.75 |
| 52 | 7850103 | Quản lý đất đai | 100 | 105 | 15 | 119 | 115 | 17.9 |

---

**Nơi nhận:**  
- Các khoa;  
- Phòng CTSV&HTDN;  
- Trung tâm Số và Học liệu;  
- Đăng website trường;  
- Lưu: VT, ĐT.  

<br />

**HIỆU TRƯỞNG**  
*(Đã ký và đóng dấu)*  

**PGS.TS. Đoàn Đức Tùng**`,
      raw_text: `<!-- Trang 12 --
 11. Thông tin về tuyển sinh của 2 năm gần nhất (tiếp theo)
 STT  Mã ngành  Tên ngành  Chỉ tiêu (2024)  Trúng tuyển (2024)  Điểm chuẩn (2024)  Chỉ tiêu (2025)  Trúng tuyển (2025)  Điểm chuẩn (2025) 
 :---:  :---:  :---  :---:  :---:  :---:  :---:  :---:  :---: 
 33  7460112  Toán ứng dụng  55  47  15  60  60  19.5 
 34  7480103  Kỹ thuật phần mềm  61  50  15  61  58  19.5 
 35  7480107  Trí tuệ nhân tạo  52  18  15  55  50  20 
 36  7480201  Công nghệ thông tin  304  349  16.5  172  171  21.5 
 37  7510205  Công nghệ kỹ thuật ô tô  186  169  16  122  111  22.2 
 38  7510401  Công nghệ KT hoá học  50  19  15  41  47  20.5 
 39  7510605  Logistics và QL chuỗi cung ứng  170  218  21  184  164  23.6 
 40  7520116  Kỹ thuật cơ khí động lực  0  0  0  33  38  20.14 
 41  7520201  Kỹ thuật điện  113  143  16  144  137  20.65 
 42  7520207  Kỹ thuật điện tử - viễn thông  89  61  15  89  90  20.77 
 43  7520216  Kỹ thuật điều khiển và Tự động hóa  74  67  15  85  76  21.02 
 44  7520401  Vật lý kỹ thuật  0  0  0  57  56  18.25 
 45  7540101  Công nghệ thực phẩm  170  142  15  148  137  20.9 
 46  7580201  Kỹ thuật xây dựng  100  96  15  97  99  20.15 
 47  7620109  Nông học  50  29  15  44  39  15 
 48  7760101  Công tác xã hội  96  77  20.25  65  48  23.7 
 49  7810103  Quản trị dịch vụ du lịch và lữ hành  131  154  19.85  146  122  22.25 
 50  7810201  Quản trị khách sạn  167  128  18.35  113  90  22.65 
 51  7850101  Quản lý tài nguyên và môi trường  100  84  15  102  101  20.75 
 52  7850103  Quản lý đất đai  100  105  15  119  115  17.9 

---

Nơi nhận:  
- Các khoa;  
- Phòng CTSV&HTDN;  
- Trung tâm Số và Học liệu;  
- Đăng website trường;  
- Lưu: VT, ĐT.  

<br /

HIỆU TRƯỞNG  
(Đã ký và đóng dấu)  

PGS.TS. Đoàn Đức Tùng`,
      bounding_boxes: [
        {
          id: "bbox_p12_01",
          page_number: 12,
          type: "table",
          coordinates: {
            x: 14.4,
            y: 5.9,
            width: 85.6,
            height: 50.1,
          },
          label: "table",
          confidence: 0.98,
          content_snippet: "Bảng số liệu tuyển sinh",
        },
        {
          id: "bbox_p12_02",
          page_number: 12,
          type: "text",
          coordinates: {
            x: 14.3,
            y: 59.8,
            width: 66.7,
            height: 8.8,
          },
          label: "text",
          confidence: 0.98,
          content_snippet: "Đoạn văn bản quy định",
        },
        {
          id: "bbox_p12_03",
          page_number: 12,
          type: "text",
          coordinates: {
            x: 59.4,
            y: 73.1,
            width: 25.0,
            height: 1.1,
          },
          label: "text",
          confidence: 0.98,
          content_snippet: "Đoạn văn bản quy định",
        },
        {
          id: "bbox_p12_stamp",
          page_number: 12,
          type: "stamp",
          coordinates: {
            x: 58.0,
            y: 68.5,
            width: 34.0,
            height: 16.0,
          },
          label: "Dấu & Ký",
          confidence: 0.99,
          content_snippet: "HIỆU TRƯỞNG PGS.TS. Đoàn Đức Tùng (Đã ký và đóng dấu)",
        },
      ],
      regions: [
        {
          id: "reg_p12_01",
          page_number: 12,
          title: "11. Bảng Điểm chuẩn 2 năm (STT 33-52)",
          type: "table",
          confidence: 0.99,
          reading_order: 1,
          details: "Các ngành kỹ thuật, CNTT, du lịch, đất đai",
        },
        {
          id: "reg_p12_02",
          page_number: 12,
          title: "Nơi nhận Văn bản Hành chính",
          type: "text",
          confidence: 0.97,
          reading_order: 2,
          details: "Các khoa, Phòng CTSV&HTDN, Trung tâm Số và Học liệu",
        },
        {
          id: "reg_p12_03",
          page_number: 12,
          title: "Con dấu Tròn Đỏ & Chữ ký Hiệu trưởng",
          type: "stamp",
          confidence: 0.99,
          reading_order: 3,
          details: "PGS.TS. Đoàn Đức Tùng — Hiệu trưởng Trường Đại học Quy Nhơn",
        },
      ],
    },
    {
      page_number: 13,
      word_count: 427,
      line_count: 40,
      image_url: "/ocr-cache/doc_ts_2026/page_13.jpg",
      markdown_content: `<!-- Trang 13 -->
# PHỤ LỤC 1
## Danh sách các ngành xét tuyển thẳng và ưu tiên xét tuyển

| Tên môn thi HSG quốc gia | Tên ngành đào tạo | Mã ngành |
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
| Tin học | Kỹ thuật phần mềm | 7480103 |`,
      raw_text: `<!-- Trang 13 --
 PHỤ LỤC 1
 Danh sách các ngành xét tuyển thẳng và ưu tiên xét tuyển

 Tên môn thi HSG quốc gia  Tên ngành đào tạo  Mã ngành 
 :---  :---  :---: 
 Toán  Sư phạm Toán học  7140209 
 Toán  Toán ứng dụng  7460112 
 Toán  Khoa học dữ liệu  7460108 
 Toán  Trí tuệ nhân tạo  7480207 
 Toán  Công nghệ thông tin  7480201 
 Vật lí  Sư phạm Vật lý  7140211 
 Vật lí  Kỹ thuật điện  7520201 
 Vật lí  Sư phạm Khoa học tự nhiên  7140247 
 Vật lí  Vật lý kỹ thuật (Công nghệ gia công, đóng gói và kiểm thử vi mạch)  7520401 
 Vật lí  Kỹ thuật điện tử - viễn thông (Thiết kế vi mạch)  7520207 
 Hóa  Sư phạm Hóa học  7140212 
 Hóa  Công nghệ thực phẩm  7540101 
 Hóa  Công nghệ kỹ thuật Hóa học  7510401 
 Hóa  Sư phạm Khoa học tự nhiên  7140247 
 Hóa  Hóa học (Hóa dược, Hóa mỹ phẩm)  7440112 
 Sinh  Sư phạm Sinh học  7140213 
 Sinh  Nông học  7620109 
 Sinh  Sư phạm Khoa học tự nhiên  7140247 
 Ngữ văn  Sư phạm Ngữ văn  7140217 
 Ngữ văn  Việt Nam học  7310630 
 Ngữ văn  Quản lý nhà nước  7310205 
 Ngữ văn  Luật  7380101 
 Lịch sử  Sư phạm Lịch sử  7140218 
 Lịch sử  Đông phương học  7310608 
 Lịch sử  Quản lý nhà nước  7310205 
 Lịch sử  Luật  7380101 
 Lịch sử  Sư phạm Lịch sử - Địa lý  7140249 
 Địa lí  Sư phạm Địa lý  7140219 
 Địa lí  Đông phương học  7310608 
 Địa lí  Sư phạm Lịch sử - Địa lý  7140249 
 Tin học  Sư phạm Tin học  7140210 
 Tin học  Công nghệ thông tin  7480201 
 Tin học  Trí tuệ nhân tạo  7480107 
 Tin học  Kỹ thuật phần mềm  7480103 `,
      bounding_boxes: [
        {
          id: "bbox_p13_01",
          page_number: 13,
          type: "text",
          coordinates: {
            x: 25.6,
            y: 6.3,
            width: 53.4,
            height: 4.1,
          },
          label: "text",
          confidence: 0.98,
          content_snippet: "Đoạn văn bản quy định",
        },
        {
          id: "bbox_p13_02",
          page_number: 13,
          type: "table",
          coordinates: {
            x: 7.8,
            y: 10.7,
            width: 89.3,
            height: 79.2,
          },
          label: "table",
          confidence: 0.98,
          content_snippet: "Bảng số liệu tuyển sinh",
        },
      ],
      regions: [
        {
          id: "reg_p13_01",
          page_number: 13,
          title: "PHỤ LỤC 1: Tiêu đề Văn bản",
          type: "header",
          confidence: 0.99,
          reading_order: 1,
          details: "Danh sách các ngành xét tuyển thẳng và ưu tiên xét tuyển",
        },
        {
          id: "reg_p13_02",
          page_number: 13,
          title: "Bảng Môn thi HSG Quốc gia & Ngành tương ứng",
          type: "table",
          confidence: 0.99,
          reading_order: 2,
          details: "Toán, Vật lí, Hóa, Sinh, Ngữ văn, Lịch sử, Địa lí, Tin học, Tiếng Anh",
        },
      ],
    },
    {
      page_number: 14,
      word_count: 75,
      line_count: 9,
      image_url: "/ocr-cache/doc_ts_2026/page_14.jpg",
      markdown_content: `<!-- Trang 14 -->
### PHỤ LỤC 1 (tiếp theo)

| Tên môn thi HSG quốc gia | Tên ngành đào tạo | Mã ngành |
| :--- | :--- | :---: |
| Tiếng Anh | Sư phạm Tiếng Anh | 7140231 |
| Tiếng Anh | Ngôn ngữ Anh | 7220201 |
| Tiếng Anh | Đông phương học | 7310608 |
| Tiếng Trung | Ngôn ngữ Trung Quốc | 7220204 |`,
      raw_text: `<!-- Trang 14 --
 PHỤ LỤC 1 (tiếp theo)

 Tên môn thi HSG quốc gia  Tên ngành đào tạo  Mã ngành 
 :---  :---  :---: 
 Tiếng Anh  Sư phạm Tiếng Anh  7140231 
 Tiếng Anh  Ngôn ngữ Anh  7220201 
 Tiếng Anh  Đông phương học  7310608 
 Tiếng Trung  Ngôn ngữ Trung Quốc  7220204 `,
      bounding_boxes: [
        {
          id: "bbox_p14_01",
          page_number: 14,
          type: "table",
          coordinates: {
            x: 7.8,
            y: 5.9,
            width: 89.3,
            height: 4.1,
          },
          label: "table",
          confidence: 0.98,
          content_snippet: "Bảng số liệu tuyển sinh",
        },
      ],
      regions: [
        {
          id: "reg_p14_01",
          page_number: 14,
          title: "PHỤ LỤC 1 (Tiếp theo): Môn Tiếng Trung",
          type: "table",
          confidence: 0.99,
          reading_order: 1,
          details:
            "Môn Tiếng Trung xét tuyển ngành Ngôn ngữ Trung Quốc (7220204) và Đông phương học",
        },
      ],
    },
  ],
};
