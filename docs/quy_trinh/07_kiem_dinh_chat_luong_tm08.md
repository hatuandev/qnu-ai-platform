# QUY TRÌNH 07: KIỂM ĐỊNH CHẤT LƯỢNG RAGAS TM-08 (CONTINUOUS EVALUATION TM-08 FLOW)

Tài liệu này đặc tả quy trình đánh giá chất lượng tự động của hệ thống RAG và các Trợ lý AI dựa trên 3 chỉ số Ragas cốt lõi đáp ứng yêu cầu kỹ thuật đề tài nghiên cứu cấp trường (**Mã tiêu chuẩn: QNU TM-08**).

---

## 1. Sơ Đồ Quy Trình Đo Lường & Báo Động Lệch Chuẩn (Evaluation Flow)

```mermaid
flowchart TD
    CRON[Lịch chạy định kỳ / Kích hoạt thủ công qua API: POST /evaluation/runs] --> SEED[Nạp Bộ Dữ Liệu Benchmark Chuẩn QNU: 100 câu hỏi]
    
    SEED --> RUN_LOOP[Vòng lặp đánh giá từng mẫu kiểm thử]
    
    subgraph METRICS_CALCULATION [Tính Toán 3 Chỉ Số Ragas TM-08]
        RUN_LOOP --> M1[1. Faithfulness: Tính tỷ lệ câu khẳng định có căn cứ trong tài liệu]
        RUN_LOOP --> M2[2. Answer Relevance: Tính mức độ trả lời trúng trọng tâm câu hỏi]
        RUN_LOOP --> M3[3. Context Precision: Tính độ chính xác của các đoạn ngữ cảnh trích xuất]
        RUN_LOOP --> M4[4. Hallucination Detection: Quét số liệu, năm, mã ngành ngoài ngữ cảnh]
    end

    M1 --> AGGREGATE[Tổng hợp Điểm Trung bình của Đợt Chạy]
    M2 --> AGGREGATE
    M3 --> AGGREGATE
    M4 --> AGGREGATE

    AGGREGATE --> EVAL_GATE{Đối Soát Ngưỡng Chuẩn QNU TM-08?}
    
    EVAL_GATE -->|Faithfulness >= 0.90<br>Relevance >= 0.85<br>Precision >= 0.80<br>Zero Hallucination| PASS[ĐẠT CHUẨN TM-08 (PASSED)<br>Lưu báo cáo vào MinIO & Cho phép tiếp tục phục vụ]
    
    EVAL_GATE -->|Vi phạm bất kỳ ngưỡng nào| FAIL[CẢNH BÁO LỆCH CHUẨN (DRIFT DETECTED)<br>Gửi thông báo Telegram/Email cho Quản trị viên<br>Tạm khóa phiên bản Assistant vừa cập nhật]
```

---

## 2. Các Chỉ Số Đánh Giá Chuẩn QNU TM-08

| Chỉ Số Đánh Giá | Ngưỡng Chuẩn TM-08 | Công Thức / Cơ Chế Tính | Ý Nghĩa Kỹ Thuật |
| :--- | :---: | :--- | :--- |
| **Faithfulness** (Độ trung thực) | $\mathbf{\ge 0.90}$ | Tỷ lệ câu khẳng định trong câu trả lời có bằng chứng trực tiếp trong các Chunks trích xuất. Tự động đạt 1.0 khi kích hoạt No-Answer Policy. | **Triệt tiêu bịa đặt**: Bảo đảm Trợ lý không nói sai lệch so với văn bản chính thức của trường. |
| **Answer Relevance** (Độ liên quan) | $\mathbf{\ge 0.85}$ | Đo độ phủ từ khóa của câu hỏi trong câu trả lời kết hợp hệ số phạt độ dài (length penalty). | **Trúng trọng tâm**: Tránh trả lời vòng vo, né tránh hoặc quá ngắn cụt lủn. |
| **Context Precision** (Độ chính xác ngữ cảnh) | $\mathbf{\ge 0.80}$ | Tỷ lệ các Chunks trích xuất từ Qdrant/PostgreSQL có chứa thông tin cần thiết của Ground Truth. | **Hiệu quả truy xuất**: Bảo đảm tầng RAG chọn đúng văn bản liên quan nhất lên đầu. |
| **Hallucination Detection** (Bắt số liệu ảo) | **0 vi phạm** | Bộ lọc Regex quét tìm các con số (điểm chuẩn, học phí, số điện thoại) xuất hiện trong câu trả lời nhưng không có trong tài liệu gốc. | **Cảnh báo khẩn cấp**: Phát hiện ngay lập tức nếu AI tự bịa ra điểm thi hay hotline giả mạo. |

---

## 3. Quản Trị & Lưu Trữ Kết Quả Đánh Giá
- Mọi đợt kiểm định đều được lưu bản ghi vào bảng CSDL `evaluation_runs`.
- Báo cáo chi tiết từng câu hỏi (kèm lý do đạt/hỏng) được xuất thành tệp JSON/Excel lưu trữ bền vững tại **MinIO** (`artifacts/eval_report_UUID.xlsx`).
