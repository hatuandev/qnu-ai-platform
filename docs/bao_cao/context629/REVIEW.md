# Context629 — Xác minh PaddleOCR nội bộ

Ngày 2026-10-25, người dùng xác nhận đã test được và yêu cầu kiểm tra lại `http://100.105.13.53:8080/layout-parsing`. Sau câu hỏi ở Context628 về vùng gửi/đích nhận, lượt này chỉ gửi **một ảnh PNG vùng đầu trang 1** của PDF quy đổi điểm đã chọn, tới đúng endpoint Paddle nội bộ, không fallback cloud.

**Endpoint hoạt động: HTTP200, errorCode0, 1,578 giây, một request, một trang trả về.** Dùng `PaddleOCRVLAdapter.extract` hiện có, giữ nguyên Redis capacity lease; không gọi hàm bỏ qua giới hạn và không đổi cấu hình đang chạy.

## Kết quả thực chạy

| Test ID | Kết quả | Exit code | Phạm vi |
|---|---|---|---|
| OCR629-HEADER-LIVE | PASS | 0 | Adapter thật → endpoint thật; HTTP200, 6.004 bytes phản hồi, 788 ký tự văn bản, một trang |
| OCR629-FIELDS-OFFLINE | PASS về tái hiện | 0 | Hàm `_field_lines` hiện có đọc Markdown chỉ có ngày; đọc raw block có cả số và ngày |
| Postcheck | PASS | 0 trong probe | Provider config, mã app, PDF nguồn giữ nguyên; DB chỉ đọc |
| Toàn PDF/Compiler/Quality Gate | NOT RUN | — | Không dùng kết quả crop để chứng nhận toàn bộ tài liệu |

Lệnh từ `backend`: `.venv/Scripts/python.exe ../.antigravity-bridge/validation/context629_ocr_probe.py` và `context629_field_audit.py`. Chạy bằng quyền cần thiết để tiến trình đọc runtime/kết nối endpoint được phép, không sửa quyền hay chính sách hệ thống.

[Biên nhận live](../../../backend/storage/context629/result.json), [đối soát trường](../../../backend/storage/context629/field-audit.json), [postcheck](../../../backend/storage/context629/postcheck.json), [Markdown OCR](../../../backend/storage/context629/header-ocr.md). Phản hồi gốc và PNG lưu qua LocalStorageDriver trong `backend/storage/context629/objects`, không đưa vào Git.

## Nguyên nhân lỗi trước và lỗi tích hợp mới xác minh

**Không có bằng chứng endpoint Paddle hỏng trong Context628.** Lượt thử khi đó bị Redis cô lập chặn trước khi inference được gửi; lần gọi sau bị auto-review từ chối phạm vi egress. Lượt hiện tại được người dùng chỉ định endpoint cụ thể và đã gọi thành công qua cơ chế capacity thật. Không đổi lịch sử Context628 thành OCR PASS; đây là phép thử mới.

Trong phản hồi thật lần này, `prunedResult.parsing_res_list` có block `header` chứa `Số: 123 /TB-HĐTS`, cùng bbox của vùng nguồn. Markdown do server trả không chứa block header đó. Ngày `Gia Lai, ngày 11 tháng 7 năm 2026` nằm trong block text và có trong Markdown.

`header_rescue.rescue_header` hiện lấy `response.pages[0].extracted_text` để tìm các trường. Replay đúng hàm `_field_lines` cho kết quả:

- Chỉ Markdown: tìm được ngày, **không có document_number**.
- Raw block text: tìm được `Số: 123/TB-HĐTS` và ngày 11/7/2026.

Vì vậy có khoảng hở ở chỗ app chọn đầu vào cho header rescue: dữ liệu đã có trong phản hồi cấu trúc nhưng chưa được đưa vào bộ tìm trường. Adapter vẫn giữ raw evidence/blocks; không phải toàn bộ dữ liệu OCR bị mất.

Hướng sửa phù hợp là kết hợp các block header có bbox hợp lệ với vùng crop, giữ provenance, kiểm tra tính duy nhất và đối chiếu trường native trước khi chấp nhận đề xuất số/ngày. Không thay toàn native text bằng OCR và không tự sửa lỗi chữ. Bản OCR vẫn có vài từ nhận sai như “chính quyền”; HTTP200 không chứng minh toàn văn hoàn toàn chính xác.

**Chưa sửa mã ứng dụng hoặc áp dụng kết quả này vào revision.** Lỗi header bảng nền trắng/nối trang và vùng hình của Context628 vẫn còn; chưa chạy Compiler, nạp vector hay xuất bản. Kiểm thử toàn ứng dụng không chạy vì không sửa source.

DB chỉ mở transaction READ ONLY để đọc provider đã được cấu hình và kiểm hash sau lượt gọi; không tạo database mới, không migration, không ghi usage/domain/config. MinIO/Qdrant/DB/Redis config đã kiểm là local; Storage đầu ra dùng thư mục riêng. Redis chỉ sử dụng acquire/renew/release bình thường của adapter. Không có API key trong file/log. Không đổi model, restart, commit hoặc push.
