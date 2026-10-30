# Compiler tài liệu lớn — chia phần và phục hồi

## Những gì đã triển khai

- Giữ snapshot đầy đủ. Khi request một lượt vượt giới hạn, lập manifest các phần theo block/hàng bảng, bỏ evidence map và ảnh Base64 khỏi request từng phần. Header, điều kiện và chú thích được giữ làm context. Bảng literal đính kèm từ nguồn, không nhờ model viết lại.
- Mỗi phần có input/schema hash, provider/config, trạng thái, raw response, kết quả dẫn xuất và usage quan sát được. Một phần/hàng và context bắt buộc không vừa ngân sách sẽ báo lỗi, không tự cắt nguồn.
- Compiler dùng lease/fencing hiện có. Review giữ token thực thi khi tiếp quản; kiểm tra scope/provider/expiry trước và sau model call, không để lượt cũ ghi vào lượt mới. Lượt in-flight không có raw giữ uncertain, không gửi lại mù quáng.
- MD/JSON tổng hợp được tạo từ các phần đã xong. Mỗi generation có hai blob đã đọc lại kiểm hash và con trỏ DB; bản partial không đi vào publication. Blob có đường dẫn riêng để writer cũ không ghi đè generation của writer mới.
- Review nhiều phần kiểm mỗi source/draft unit đúng một lần, giữ nguồn trích dẫn làm context. Không tự bỏ header/nguồn chỉ để request vừa ngân sách. Report tổng hợp và publication gate hiện có giữ nguyên.
- Run cũ vẫn có đường đọc/biên soạn một lượt; run chia phần dùng workflow/v2. Không đổi model/capacity/quota/credential.

- Planner v2 chia cả khi input vừa nhưng lượng nội dung lớn so với output. Proxy UTF-8 của owned và framing/citation chiếm tối đa25% output khi lập phần; phần còn lại dành cho suy luận và độ phình JSON. Một block/hàng quá mức báo lỗi riêng, không cắt nguồn.
- Prompt v2 gửi rõ owned/context_only, bảng literal do backend ghép nên không diễn giải lại từng ô. Input/output/schema hash được chốt trước gọi.

## Giới hạn minh bạch

Hiện vẫn dùng cận trên byte UTF-8 cho input, chưa phải tokenizer model; output dùng proxy lập kế hoạch riêng. Proxy không bảo đảm model luôn kết thúc trong ngân sách. Phần nguyên tử/context bắt buộc quá lớn sẽ FAIL rõ, không tự cắt nội dung.

Chỉ tái sử dụng phần đã lưu trong cùng run/snapshot và cùng cấu hình. Nguồn/revision thay đổi tạo run mới; chưa tái dùng cache xuyên revision để tránh gắn sai citation. Review semantic vẫn có thể báo thiếu/nghi ngờ; coverage ID không chứng minh nội dung đúng.

Chưa thêm màn hình giao diện riêng; API progress và bản partial cung cấp trạng thái thật, E2E admissions đã nối progress. Review POST vẫn thực thi đồng bộ; client cần đủ thời gian cho nhiều phần. Chưa áp dụng migration hoặc chạy nghiệm thu trong phiên triển khai.

## Áp dụng vào phiên đang dở

Dừng đúng cửa sổ serve bằng Ctrl+C, sau đó:

```powershell
.\test-v1-e2e.ps1 serve
```

Serve chạy `alembic upgrade head` theo cơ chế hiện có; migration mới là `0008_compilation_segments`. Không cleanup/init nếu đang tiếp tục phiên chưa purge. Chờ sẵn sàng rồi ở cửa sổ thứ hai:

```powershell
.\test-v1-e2e.ps1 run admissions-compilation --headed
.\test-v1-e2e.ps1 run admissions-publication --headed
.\test-v1-e2e.ps1 run admissions-chat --headed
```

Chỉ chạy tiếp sau PASS. Đã đối chiếu lượt lỗi phần1 phiên hiện tại: output8192 toàn suy luận, content rỗng. Khi người dùng chạy lại admissions-compilation, helper cho phép **một** lượt phục hồi riêng cho failed/chat_output_truncated, cùng provider, chưa review/version. Lượt mới dùng JSON Schema, planner v2 và output ceiling hợp lệ từ ModelOps; không đổi mặc định compiler8192 hoặc cấu hình DB. Khóa phục hồi gắn ID lượt lỗi và policy; checkpoint giữ lịch sử. Nếu POST xong mất kết nối, chạy lại dùng cùng khóa. Không lặp phục hồi hoặc tự retry uncertain/cancelled/lỗi khác.

## Lệnh kiểm chứng dành cho người dùng

Chưa chạy các lệnh bên dưới. Unit từ repo root:

```powershell
Push-Location backendV1
.\.venv\Scripts\python.exe -m pytest tests/unit/test_compilation_segments_744.py tests/unit/test_compilation_review_parts_744.py tests/unit/test_compilation_fencing_744.py
Pop-Location
```

Integration cần DB/cache test theo cấu hình quy định, không dùng DB phục vụ:

```powershell
Push-Location backendV1
.\.venv\Scripts\python.exe -m pytest tests/integration/test_compiler_segments_api_744.py tests/integration/test_compiler_review_652.py tests/integration/test_compiler_queue_645.py tests/integration/test_compiler_edits_654.py tests/integration/test_publication_646.py
Pop-Location
```

Không coi thiếu môi trường hoặc NOT RUN là PASS. Gate rộng lịch sử còn lỗi vẫn giữ FAIL cho đến khi được kiểm chứng lại.
