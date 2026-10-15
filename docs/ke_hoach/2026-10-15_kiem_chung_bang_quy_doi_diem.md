# Kiểm chứng bảng quy đổi điểm tuyển sinh 2026

## Kết quả đọc nguồn

Cập nhật phiên481: đã tạo revision3 `ks_rev_259de8772948` chờ duyệt, khôi phục đủ cột;
bản active vẫn là revision2 thiếu cột, chưa vector/publish hoặc kích hoạt rule. Xem
[nhật ký481](../nhat_ky/2026-10-15_phien_481_khoi_phuc_bang_quy_doi_cho_duyet.md).

Nguồn: `docs/tai_lieu/tuyen_sinh/Thong_bao_quy_doi_tuong_duong_QNU_2026_Chinh thuc-signed.pdf`.
SHA-256: `96207cca90ecd30df23d9ffcf74fb982a6277e4d89b08270e3465a4a2bd5dc8e`.

- PDF có 5 trang; nội dung chính nêu nội suy tuyến tính giữa hai mốc bách phân vị liền kề, quy về THPT của tổ hợp gốc.
- Phụ lục 1 ở trang 3 có 23 cột: Top %, ĐNL và 7 nhóm tổ hợp, mỗi nhóm gồm SPT, HB, THPT; có 22 hàng dữ liệu sau hai hàng tiêu đề.
- Phụ lục 2 ở trang 4–5 có 50 hàng ánh xạ tổ hợp. Không suy ánh xạ từ tên môn hoặc từ ví dụ prompt.
- Nguồn chỉ quy định làm tròn một lần ở cuối đến hai chữ số thập phân; chưa xác định rõ quy tắc xử lý đúng điểm giữa (half-up hay half-even). Chính sách này cần người phụ trách xác nhận trước khi kích hoạt rule, không tự gán là nội dung văn bản.
- Bản canonical đang xuất bản được kiểm tra trong phiên chỉ giữ 9 cột của Phụ lục 1, thiếu HB/THPT. Không được dùng vị trí cột SPT thay cho THPT.

Đối chiếu số độc lập trên bảng gốc: ĐNL 780, tổ hợp A01 nằm giữa hai hàng ĐNL 764 / THPT 20,75 và ĐNL 790 / THPT 21,50. Nội suy cho 21,211538…; làm tròn đến hai chữ số được 21,21. Đây là kiểm tra bằng nguồn PDF, **không phải bằng chứng chatbot production đã tính được**.

## Đã triển khai trong mã

- Endpoint có xác thực `POST /platform/v1alpha1/rag/scores/convert`; tenant/workspace lấy từ actor, không từ body. Chỉ nhận collection, năm, phương thức nguồn, tổ hợp và điểm dạng chuỗi.
- Engine Decimal chỉ chấp nhận `piecewise_linear`, không eval công thức OCR, không clamp/ngoại suy. Kiểm tra cùng hàng, đúng cột, mapping, source/hash và index đang xuất bản; lỗi hạ tầng không biến thành câu trả lời giả.
- Rule chỉ được lấy từ cấu hình collection trong DB (`score_conversion_rules`), không lấy từ runtime_policy, body hoặc lời model. Chưa có rule nào được thêm vào DB trong phiên này.
- Rule khai báo năm, reviewer/timezone, binding/index/source/hash, phương thức và nhãn cột, mapping có bằng chứng ô, các cặp điểm cùng hàng, bằng chứng công thức/làm tròn, độ chính xác và chế độ làm tròn đã duyệt.
- Chat chỉ dùng model phân loại ý định và trích đầu vào; không cho model tính hay viết lại kết quả số. Thiếu đầu vào hỏi lại; thiếu rule/bảng đã duyệt thì chưa tính. Chưa cung cấp giao diện quản trị rule hoặc đăng ký function-calling Tool Gateway.

## Cổng bắt buộc trước khi dùng thực tế

1. Đối chiếu hình học đủ 23 cột, 22 hàng và toàn bộ 50 mapping; giữ liên kết trang/ô, không chỉ tin văn bản nối dòng.
2. Sửa/duyệt bản bóc tách qua quy trình nguồn của app, tạo revision mới và chỉ xuất bản sau kiểm tra. Không sửa âm thầm canonical đang phục vụ chatbot.
3. Xác nhận chính sách làm tròn ở trường hợp đúng điểm giữa; lập rule cho từng năm/phương thức/tổ hợp gốc bằng các fact ID và hash của revision mới. Không copy ID từ nháp này.
4. Người có quyền quản trị duyệt rule; kiểm tra quyền ghi metadata theo quy trình triển khai trước khi cấu hình. Trường `status=verified` trong JSON không thay thế nghiệp vụ phê duyệt.
5. Chạy đối chiếu số độc lập các mốc, điểm giữa, ngoài khoảng, sai năm/phương thức, thay revision và lỗi DB. Chỉ mở sử dụng sau khi cả nguồn lẫn rule được duyệt.

Lệnh trích nháp đọc-only: `python -m scripts.inspect_conversion_pdf --pdf <source.pdf> --output <new-draft.json>`.
Nháp local phiên này: `backend/storage/rag_enumeration_480/conversion_pdf_draft.json`, trạng thái `draft_not_active`; không import, không commit dữ liệu thô.

## Giới hạn nghiệm thu

Đã kiểm tra engine bằng fixture có provenance và đối chiếu phép tính độc lập trong PDF. Chưa chạy kiểm thử model thật, chưa 20/82 câu, chưa kích hoạt dữ liệu quy đổi. Không thay model, API key, nguồn, vector, publication hoặc DB schema. Phần engine hoàn thành không đồng nghĩa toàn bộ tính năng quy đổi đã sẵn sàng production.
