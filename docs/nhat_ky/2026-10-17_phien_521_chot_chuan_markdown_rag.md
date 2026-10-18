# Phiên 521 — Chốt file chuẩn Markdown RAG

## Yêu cầu và phạm vi

Người dùng yêu cầu một file MD chuẩn kết hợp lõi Universal, quy tắc dữ liệu chọn
lọc từ v1 và chỉ mục dẫn xuất. Chỉ tạo đặc tả/mẫu dùng lại; không triển khai parser,
không sửa ba file tham khảo trong Downloads, không nạp lại nguồn hay reset DB.

## Kết quả

- Tạo [chuẩn v1.0](../quy_trinh/13_chuan_markdown_rag_v1.md): một cú pháp YAML/
  `rag:block`, loại khối tổng quát, vị trí nguồn, parent/context refs, bảng GFM
  hoặc records, trạng thái ô và dữ liệu chuẩn hóa/thời gian theo field.
- Giữ nguyên văn, raw/provenance; không coi summary/QA là nguồn độc lập. Giá trị
  duyệt trong file không cấp quyền, không publish hoặc kích hoạt công cụ.
- Chỉ mục do app/script sinh theo manifest/revision/scope, có members, đơn vị
  đếm và coverage; partial không được nhận tổng đầy đủ. Không gắn với Top K=5.
- Ghi rõ parser hiện chưa hỗ trợ đầy đủ; tài liệu thiết kế không là nghiệm thu
  ingestion/runtime. Tái dùng lifecycle và bundle hiện có khi triển khai sau.
- Đồng bộ mục lục quy trình, nhật ký, WORK_LOG và PROJECT_CONTEXT; giữ lịch sử.

## Kiểm chứng

- Chạy kiểm tra chỉ đọc bằng `backend/.venv/Scripts/python.exe` từ repo root:
  UTF-8 không BOM/LF, parse YAML frontmatter và metadata của hai mẫu Markdown,
  ID/parent/context refs của 5 khối, metadata chỉ mục partial và liên kết local.
  PASS, exit 0. Đây là kiểm tra cấu trúc ví dụ, không phải validator production.
- Kiểm tra cuối mở rộng: 7 file UTF-8/LF, parent không chu trình, columns/fields,
  4 liên kết trong các tài liệu mới và mục lục PASS, exit 0. Script kiểm tra ban
  đầu đòi số phiên 521 trong mục lục quy trình nên FAIL; sửa đúng phép kiểm thành
  liên kết chuẩn số 13, không thay nội dung để che lỗi.
- `git diff --check` theo 7 file: PASS, exit 0; Git cảnh báo cấu hình checkout
  có thể đổi LF thành CRLF sau này, bytes kiểm tra hiện tại là LF.
- NOT RUN: Pytest/build, DB, embedding/LLM, index/publish, UI và benchmark; task
  thuần tài liệu theo gate của repo. Không thay baseline test bằng kết quả tài liệu.

## Bước tiếp theo

Chỉ khi được giao triển khai: parser/validator/mapping rồi thử tài liệu đại diện,
giữ MD cũ và publication hiện có. Không mặc định migration/reindex toàn kho,
restart/deploy hay Git commit/push.
