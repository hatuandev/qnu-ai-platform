# Báo cáo Tổng kết: Pipeline Xử lý Excel (.xlsx) & Tối ưu Lập chỉ mục RAG

**Thời điểm hoàn tất:** 22/11/2026  
**Môi trường kiểm thử:** QNU AI Platform (Backend V1 + Worker V1 + Frontend V2 + Qdrant + LLM `qwen3.8-27b-q4`)  
**Nhánh Git:** `feat/v1-user-workflow`

---

## 1. Cấu hình Giới hạn dòng Excel (`XLSX_MAX_ROWS`)

Nhằm bảo vệ hệ thống khỏi tình trạng quá tải bộ nhớ và treo worker khi người dùng tải lên các tệp bảng tính khổng lồ, hệ thống đã bổ sung cơ chế kiểm soát số dòng dữ liệu an toàn và minh bạch:

- **Biến cấu hình:** `XLSX_MAX_ROWS` trong `Settings` (`backendV1/qnu/platform/config.py`).
  - **Giá trị mặc định:** `500` dòng dữ liệu/bảng tính.
  - **Biến môi trường tương ứng:** `QNU_XLSX_MAX_ROWS` (cho phép quản trị viên ghi đè linh hoạt qua Docker / Dokploy, ví dụ: `QNU_XLSX_MAX_ROWS=1000`).
- **Nguyên tắc tính số dòng dữ liệu thực tế:**
  - Tự động bỏ qua các dòng hoàn toàn rỗng trong sheet.
  - Tự động nhận diện và bỏ qua dòng tiêu đề banner ở đầu sheet.
  - Tự động lọc bỏ các dòng công thức / tổng kết cuối bảng (`=SUM(...)`, `"Tổng cộng"`).
  - Trừ đi 1 dòng Header của bảng để tính ra số dòng dữ liệu thực tế `data_rows`.
- **Thông báo lỗi minh bạch (HTTP 422 `xlsx_row_limit_exceeded`):**
  - **Tuyệt đối không cắt âm thầm:** Hệ thống loại bỏ hoàn toàn khối mã cắt dữ liệu ngầm cũ (`xlsx_table_truncated`).
  - Khi số dòng dữ liệu thực tế `len(data_rows) > XLSX_MAX_ROWS`, tiến trình lập tức dừng lại và trả về thông điệp tiếng Việt cụ thể:
    > *"Bảng tính '{sheet_name}' chứa {len(data_rows)} dòng dữ liệu, vượt quá giới hạn tối đa cho phép ({max_rows} dòng). Vui lòng tách nhỏ tệp Excel hoặc cấu hình tăng biến XLSX_MAX_ROWS."*

---

## 2. Cơ chế Xử lý Bảng, Ngân sách Chunking & 2 Điểm nghẽn Tệp lớn

### 2.1. Cơ chế đã tối ưu thành công
1. **Lược bỏ cột mẫu rỗng 100% (`direct_xlsx.py`):**
   - Các file bảng biểu thực tế (như tài nguyên thư viện 32 cột) thường chứa nhiều cột template trống hoàn toàn (ISBN, Ngôn ngữ, Tóm tắt,...). Khi tuần tự hóa sang JSON cấu trúc evidence, mỗi ô rỗng ngốn ~85 bytes.
   - Code tự động lọc bỏ các cột rỗng này (chỉ giữ lại cột có dữ liệu thực hoặc thuộc dải ô gộp `merged_cells`), giúp kích thước 1 dòng dữ liệu + header giảm từ **8.613 bytes** xuống **5.754 bytes**.
2. **Ngân sách chia nhóm thích ứng (`chunking.py`):**
   - Giới hạn trần `maximum = 8.160 bytes` (dựa trên giới hạn token của mô hình embedding, ví dụ BGE-M3: $8.192 - 32 = 8.160$).
   - Hàm `_split_group` tách các nhóm hàng vượt ngân sách thành các phần liên tiếp (*contiguous parts*), giữ lại header và các dòng `row_span` bao phủ (`_covering_rows`) để bảo toàn 100% ngữ cảnh.
3. **Chiếu bảng và vector hóa:**
   - Dữ liệu đi qua `UniversalTableProjection` -> `Row Cards` (`build_row_card_chunks`) -> upsert Qdrant theo từng mẻ cố định **64 points / batch**.

### 2.2. Hai điểm nghẽn đã nhận diện nếu xử lý tệp lớn (~37.500 dòng)
1. **Trần số dòng bảng hệ thống (`MAX_TABLE_ROWS = 2048`):**
   - Hiện tại cấu trúc bảng `Table` trong `backendV1/qnu/domains/ocr/layout.py` giới hạn 2.048 dòng. Nếu gặp tệp 37.500 dòng, việc dồn toàn bộ vào 1 bảng sẽ gây lỗi cấu trúc hoặc vượt trần `DraftContent` (100 sections $\times$ 100 paragraphs = 10.000 paragraphs).
   - **Định hướng mở rộng:** Cần áp dụng cơ chế **Phân trang logic (Sheet Pagination)** trong `direct_xlsx.py` — chia 1 sheet lớn thành các sub-tables/sub-pages (mỗi trang logic 500 – 1.000 dòng, kế thừa nguyên vẹn Header của sheet).
2. **Bộ nhớ RAM của `openpyxl` (DOM load):**
   - `openpyxl.load_workbook(io.BytesIO(payload), data_only=True)` nạp toàn bộ DOM XML vào bộ nhớ, có thể chiếm 300MB – 600MB+ RAM cho 1 worker.
   - **Định hướng mở rộng:** Sử dụng chế độ đọc luồng `read_only=True` kết hợp `iter_rows` giải phóng bộ nhớ đệm cho các tệp vượt quy mô thông thường.

---

## 3. Kết quả Kiểm thử E2E Thực tế trên Giao diện Web Local

Kiểm thử được tiến hành trực tiếp trên trình duyệt giao diện web local (`http://127.0.0.1:3002`) kết nối trọn vẹn cụm dịch vụ:

| Kịch bản | Dữ liệu đầu vào | Kết quả trên Giao diện (UI) | Trạng thái |
|---|---|---|:---:|
| **1. Vượt ngưỡng cấu hình** | `test_xlsx_over_limit.xlsx` (**550 dòng** $> 500$) | Giao diện hiển thị thẻ màu vàng cam **`Cần kiểm tra`**; tác vụ nền báo **`Xử lý gặp lỗi`**. Chi tiết lỗi trả về mã `xlsx_row_limit_exceeded`: *"Bảng tính 'Danh mục sách quá tải' chứa 550 dòng dữ liệu, vượt quá giới hạn tối đa cho phép (500 dòng)..."* | **ĐẠT (PASS)** |
| **2. Hợp lệ trong ngưỡng** | `test_qnu_sample_library.xlsx` (**~45 dòng** $\le 500$) | Giao diện hiển thị **`Đã bóc tách`** -> **`Đã sẵn sàng duyệt và hỏi đáp`**. Mở bản nháp hiển thị trọn vẹn cả 2 bảng tính. Bấm **`Duyệt`** & phát hành sinh thành công **67 chunks / table facts**. | **ĐẠT (PASS)** |
| **3. Truy vấn Chat thực tế** | Câu hỏi: *"Sách 'American business terms Dictionary' nằm ở phòng nào và có số ĐKCB ra sao?"* | Trợ lý phản hồi chính xác 100%: phân tách đúng **Phòng Đọc Mở 2** (5 mã ĐKCB) và **Phòng Giáo trình** (7 mã ĐKCB). Hiển thị **`Xem 2 nguồn dẫn chứng đối soát`** với trace thời gian và căn cứ chuẩn xác. | **ĐẠT (PASS)** |
| **4. Lượt chat tiếp theo** | Hỏi câu tiếp theo trong cùng phiên | Trợ lý đi thẳng vào nội dung, **hoàn toàn không lặp lại lời chào** *"Chào bạn, mình là..."*. | **ĐẠT (PASS)** |

---

## 4. Các bước Triển khai / Đồng bộ lên Máy chủ (`qnu-ai-new.duckdns.org` qua Dokploy)

1. **Đẩy mã nguồn lên Git:**
   - Commit toàn bộ thay đổi và push lên nhánh `feat/v1-user-workflow` trên Git repository.
2. **Cập nhật biến môi trường trên Dokploy (nếu cần điều chỉnh ngưỡng):**
   - Trong cấu hình service Backend V1 / Worker V1 trên Dokploy, biến môi trường `QNU_XLSX_MAX_ROWS` có giá trị mặc định là `500`.
   - Nếu muốn cho phép tải các tệp Excel lớn hơn (ví dụ tối đa 1.000 dòng/tệp), thêm biến:
     ```env
     QNU_XLSX_MAX_ROWS=1000
     ```
3. **Kích hoạt Redeploy trên Dokploy:**
   - Vào bảng điều khiển Dokploy của dự án `qnu-ai-platform`.
   - Chọn ứng dụng backend/worker -> Bấm nút **Redeploy** (hoặc kích hoạt Webhook tự động deploy từ nhánh `feat/v1-user-workflow`).
   - Kiểm tra log container đảm bảo không có lỗi khởi động và worker đã nạp cấu hình `XLSX_MAX_ROWS`.
