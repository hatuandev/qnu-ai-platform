# Context613 — Đối soát ứng viên trước khi tổng hợp

## Phạm vi và cách đọc

Đã kiểm tra toàn bộ 145 assertion và 92 thực thể lưu từ Context611, đối chiếu snapshot canonical381proof và nguồn gốc ba DOCX. Không gọi LLM trong bước đối soát; không sửa nguồn, áp dụng nhãn, xóa hay gộp ứng viên.

Đây là **phân loại sơ bộ phục vụ điều tra**, không phải gold benchmark hoặc chứng nhận mọi assertion trong một nhóm đều đúng/sai. Các kết quả structural, review của model và đánh giá thủ công được giữ tách biệt. Artifact theo từng assertion nằm trong Storage thử local, không sao chép corpus vào Git.

## Kết quả định lượng

- Tất cả ID thực thể và proof tham chiếu tồn tại. Số lượng 145 được giữ nguyên trong manifest mới.
- Có 32 assertion mang giá trị nguồn chưa xác định. Không chuyển thành0 hoặc coi riêng trạng thái này là lỗi.
- Có 116 assertion chưa có vai trò thời gian xác định; không dùng năm từ tên file để lấp vào.
- Có 5 `scope.value` không phải trích đoạn nguyên văn của proof đã dẫn. Chúng giữ lỗi kiểm chứng, không được chuẩn hóa chữ để giả bằng chứng.
- Có 74 nhãn thực thể khác nhau và một thực thể chưa được dùng. Không gộp tên giữa năm/nguồn để vượt qua giới hạn64.

Phân loại sơ bộ theo mục đích topic hiện tại:

| Nhóm cần đối soát | Số assertion | Cách xử lý trong phiên |
|---|---:|---|
| Ứng viên tổng chính cần kiểm năm/điều kiện | 3 | Giữ nguyên, chưa duyệt |
| Ngữ cảnh pháp lý/phạm vi | 5 | Không biến thành một tổng mới |
| Khẳng định thiếu dữ liệu cần căn cứ phạm vi | 25 | Giữ unknown cục bộ; không suy cả tài liệu thiếu |
| Nội dung sau đại học hoặc thông tin phụ | 10 | Cần xác định mức đào tạo/phạm vi |
| Ký hiệu bảng bị diễn giải như chỉ tiêu | 24 | Cần đúng vai trò cột, không coi `x` là số |
| Bảng tiến sĩ/thạc sĩ ngoài tổng đại học đang hỏi | 44 | Giữ để kiểm relevance, không tự xóa |
| Vai trò chỉ số bị gán sai | 2 | Cần sửa đề xuất ngữ nghĩa trong lượt riêng |
| Trạng thái dự thảo của nguồn | 1 | Chỉ áp dụng cho chính nguồn ấy |
| Số khảo sát/tỷ lệ bị gán sang chỉ tiêu giáo viên | 30 | Cần header và định nghĩa chỉ số đúng |
| Ngữ cảnh đợt xét bổ sung | 1 | Không thay tổng cả mùa tuyển sinh |
| **Tổng** | **145** | **Không tự chấp thuận** |

Các nhóm không được dùng làm từ điển hoặc quy tắc lọc hardcode trong app. Artifact sơ bộ chỉ ghi đánh giá của phiên; không trở thành fact có hiệu lực.

## Ví dụ xác định từ canonical

1. Số tổng nằm dưới mục **III / 2. Trình độ thạc sĩ** của nguồn1 đã được ứng viên gán thành chỉ tiêu đại học chính quy. Vấn đề là phạm vi/mức đào tạo, không phải một số bị mất trong parser.
2. Nguồn2 có mục **II / 1. Số lượng sinh viên tham gia khảo sát**; header phân biệt số tuyển sinh, số khảo sát và tỷ lệ. Một số ứng viên dùng nhãn teacher-training cho cột khảo sát; đó là sai vai trò chỉ số.
3. Các đoạn tuyển sinh bổ sung2026 có tổng riêng của đợt. Giữ tách phạm vi này; không dùng thay tổng cả mùa.

Các proof trong lần trích cũ chưa luôn đi kèm header/heading đủ nghĩa: có bảng canonical giữ dòng tên cột nhưng context native chỉ nối tới hàng header trống. Đợt613 giữ và mở rộng closure của liên kết context đã có, không tự gán vai trò cho một dòng header chưa được chứng minh. Không chạy lại parser hoặc chỉnh artifact gốc để che vấn đề này.

## Tác động đến nghiệm thu

Các kiểm tra dung lượng đã có thể tạo trang tổng hợp, nhưng chưa được gọi là nội dung đúng hoàn toàn. Bản cuối giữ `needs_attention`, gồm cả các verdict chưa xác định, phạm vi thiếu căn cứ và debt coverage. Người dùng chưa duyệt proposal nào qua phiên này.

Bước tiếp theo về nội dung nên xử lý ngữ cảnh bảng/mục và vai trò chỉ số theo cấu trúc tổng quát, rồi chỉ trích lại các nhóm liên quan; tái sử dụng phần còn hợp lệ theo hash và policy. Không chạy lại toàn tài liệu hoặc toàn bộ model calls chỉ vì tổng hợp trước đây bị chặn dung lượng.
