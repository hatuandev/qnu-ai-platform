# Phiên 577 — Commit parser, bản đọc tài liệu và RAG

Người dùng chấp nhận kết quả hiện tại và yêu cầu commit. Phạm vi được hiểu là tạo commit local trên nhánh `main`, chưa push. Ngoại lệ này thay thế giới hạn không commit của các phiên trước, không mở rộng sang thao tác dữ liệu hoặc vận hành.

## Phạm vi

Gói bàn giao gồm các thay đổi Context568–576: cấu trúc DOCX/PDF, numbering và note có locator; API/bản đọc tài liệu và tải Markdown/JSON; phạm vi hàng, điều kiện và kiểm chứng bằng chứng RAG; regression tests và báo cáo liên quan. Không sửa thêm mã ứng dụng trong phiên này.

Chỉ stage danh sách source/test/docs đã kiểm tra. Không đưa Storage tạm, tài liệu DOCX/PDF nguồn, dữ liệu benchmark thô, credential hoặc cấu hình runtime vào commit. Không bỏ theo dõi hoặc xóa file cũ.

## Kiểm tra thực hiện trong phiên

- Đọc quy định bảo mật/Git và workflow; kiểm tra `git status --short`, `git diff --stat`, nhánh và lịch sử commit. Ban đầu index trống, nhánh `main`.
- Kiểm tra 94 file thay đổi/mới ban đầu, trong đó 58 file mới. File mới lớn nhất khoảng 30KB; không có file mới trên 500KB. PROJECT_CONTEXT lớn hơn 500KB là file đã được theo dõi từ trước.
- Quét mẫu credential, Bearer literal, URL chứa mật khẩu, private key và Base64 dài; không phát hiện mẫu nghi vấn trong phạm vi commit. Đây là kiểm tra theo mẫu, không phải chứng nhận bảo mật toàn repository.
- Kiểm tra UTF-8 không BOM và LF của các file bàn giao; đạt. `git -c core.autocrlf=false diff --check` đạt. Dùng tùy chọn Git riêng cho lệnh để giữ LF, không sửa cấu hình Git lưu trên máy.
- Kiểm tra staged diff và nội dung index trước khi tạo commit local; bằng chứng cuối cùng là commit và trạng thái Git sau commit.

## Bằng chứng ứng dụng từ phiên trước

Không chạy lại ứng dụng, gọi LLM hoặc chạy benchmark trong phiên commit. Kết quả lịch sử bản code chốt Context576: focused 393 PASS, gồm 44 regression mới; Ruff 15 file PASS. Full suite vẫn FAIL: 2949 PASS / 18 FAIL / 17 SKIP, các lỗi trùng baseline theo ID/nguyên nhân. Benchmark frozen64: tri thức 59/60 = 98,33%, social 4/4; còn P06, N18 đã PASS. B03 PASS trong diagnostic trên code chốt, không chứng nhận mọi biến thể đều đạt.

Chi tiết và giới hạn: [Validation Context576](../bao_cao/context576/VALIDATION_REPORT.md). Không đổi model/nguồn, Quality Gate, index hoặc publication; không restart/deploy/push. Các Storage tạm bị policy chặn xóa ở phiên trước tiếp tục được giữ nguyên.
