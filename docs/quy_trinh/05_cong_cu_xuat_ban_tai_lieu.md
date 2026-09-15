# QUY TRÌNH 05: CỔNG CÔNG CỤ & XUẤT BẢN TÀI LIỆU (TOOL GATEWAY & DOCUMENT EXPORT FLOW)

Tài liệu này đặc tả quy trình kết nối công cụ ngoại vi qua cơ chế Function Calling chuẩn OpenAPI, sinh tệp văn bản hành chính Word theo Nghị định 30/2020/NĐ-CP, tệp bảng tính Excel ma trận đề thi chuẩn Bloom, lưu trữ thành phẩm trên **MinIO Object Storage** và chuyển đổi PDF qua **Gotenberg 8**.

---

## 1. Sơ Đồ Quy Trình Thực Thi Công Cụ (Tool Gateway Sequence Diagram)

```mermaid
sequenceDiagram
    autonumber
    participant U as Giảng viên / Cán bộ QNU
    participant API as Backend Platform API
    participant TG as Tool Registry & Gateway
    participant TE as Tool Implementation Engine
    participant MN as MinIO Object Storage
    participant GT as Gotenberg 8 (Headless Converter)

    U->>API: Yêu cầu: "Dự thảo Thông báo lịch thi học kỳ 2"
    API->>TG: Kiểm tra quyền & đối soát Tool Schema
    TG->>TE: Kích hoạt DocumentExporterTool.execute()
    
    Note over TE: 1. Khởi tạo tài liệu Word .docx<br>2. Cài đặt font Times New Roman (Liberation Serif)<br>3. Dựng Quốc hiệu, Tiêu ngữ, Tên cơ quan ban hành<br>4. Canh lề chuẩn NĐ 30: Trên 2cm, Dưới 2cm, Trái 3cm, Phải 1.5cm
    
    TE->>TE: Đóng gói luồng byte văn bản (.docx)
    TE->>MN: Lưu trữ tệp thành phẩm vào MinIO: artifacts/thong_bao_UUID.docx
    MN-->>TE: Xác nhận lưu trữ thành công (S3 Key)

    opt Nếu người dùng yêu cầu xem trước (Preview PDF)
        TE->>GT: POST luồng Word sang Gotenberg /forms/libreoffice/convert
        GT-->>TE: Trả về luồng byte tệp PDF chuẩn in ấn
        TE->>MN: Lưu trữ tệp PDF vào MinIO: artifacts/thong_bao_UUID.pdf
    end

    TE-->>TG: Trả về ToolExecutionResult (file_name, download_url, size_bytes)
    TG-->>API: Gắn metadata vào Workflow Context
    API-->>U: Trả về kết quả kèm link tải tệp Word/PDF chính thức
```

---

## 2. Các Công Cụ Tiêu Biểu Trong Hệ Thống

### 1. `DocumentExporterTool` — Xuất Văn Bản Hành Chính Nghị Định 30/2020/NĐ-CP
- **Tiêu chuẩn kỹ thuật tuân thủ**:
  - Phông chữ: `Times New Roman` (hoặc `Liberation Serif` trong môi trường Linux Docker).
  - Canh lề trang A4: Lề trên: 20 mm; Lề dưới: 20 mm; Lề trái: 30 mm; Lề phải: 15 mm.
  - Cấu trúc: Quốc hiệu & Tiêu ngữ in đậm canh giữa; Tên cơ quan chủ quản (BỘ GIÁO DỤC VÀ ĐÀO TẠO / TRƯỜNG ĐẠI HỌC QUY NHƠN); Số & Ký hiệu văn bản; Tên loại & Trích yếu nội dung; Chữ ký & Họ tên người ký; Nơi nhận.
- **Lưu trữ**: File sinh ra được đẩy ngay lên MinIO tại prefix `artifacts/`.

### 2. `ExamMatrixExporterTool` — Xuất Ma Trận Đề Thi 4 Cấp Độ Bloom
- **Mô hình khảo thí**: Phân bổ số câu và thang điểm theo 4 cấp độ tư duy:
  1. *Nhận biết* (Recognition)
  2. *Thông hiểu* (Comprehension)
  3. *Vận dụng* (Application)
  4. *Vận dụng cao* (Advanced Application)
- **Định dạng kết xuất**: Tệp bảng tính Microsoft Excel (`.xlsx`) sử dụng thư viện `openpyxl`, tự động tính toán tổng điểm, tỷ lệ phần trăm và định dạng bảng kẻ viền chuẩn khảo thí QNU.
- **Lưu trữ**: File sinh ra được đẩy lên MinIO tại prefix `artifacts/`.

### 3. `AdmissionScoreLookupTool` — Cổng Tra Cứu Dữ Liệu Tuyển Sinh
- Tra cứu bảng điểm chuẩn các năm (2024, 2025, 2026), mã ngành, tên ngành, tổ hợp môn xét tuyển từ CSDL nội bộ mà không cần phụ thuộc vào mô hình LLM ngoại vi.
