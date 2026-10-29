# Context713 — Review tĩnh các thay đổi backendV1 hiện tại

Ngày: 2026-10-29. Yêu cầu: xem thay đổi BE và tác động, không test. Không sửa mã ứng dụng.

## Phạm vi và phương pháp

Đọc Git status/log/diff so với HEAD `c36ce562`, sáu tệp BE đã sửa và hai tệp BE chưa theo dõi (workspace navigation và test liên quan), rồi lần theo đường gọi render, job auto extraction, config/fingerprint, artifact persistence, authorization và fixture hiện có. Đọc thêm diff runner/Compose vì chúng cấp Gotenberg cho renderer. `backend/` không có diff chưa commit trong lần đọc; phần đánh giá dưới đây áp dụng cho V1. Đây không phải audit toàn bộ lịch sử hay toàn bộ backend.

Skill đối chiếu: qnu-clean-code-architect, qnu-backend-architect, qnu-knowledge-ingestion. Chỉ đọc file/Git; không gọi API, Docker, model, database hoặc chạy ứng dụng, test, lint, build, import probe.

## Các thay đổi quan sát được

- DOCX chuyển từ PyMuPDF Story sang ưu tiên Gotenberg LibreOffice, rồi tự quay về Story khi Gotenberg lỗi.
- Thêm GET processing-runs/{run_id}/pdf, đọc artifact render_pdf đã lưu để hiển thị PDF chuyển từ DOCX.
- Thêm cấu hình GOTENBERG_URL và API workspaces/resolve-route để suy workspace/collection từ workspace code và source ID có kiểm quyền.
- Runner thêm Gotenberg vào v1-infra-up; Compose giới hạn cổng3005 trên127.0.0.1. Image MinIO không đổi trong diff này.
- Không có schema migration mới trong diff chưa commit; HEAD đã chứa migration0007/native-first extraction. Không có sửa trực tiếp Compiler/RAG/ModelOps trong diff BE lần đọc này.

## Findings

### F01 — P1: Bộ chuyển đổi không được ghim, ảnh hưởng reuse và phục hồi job

Vị trí thay đổi: `backendV1/qnu/domains/ocr/artifacts/render.py:184`.

Mỗi lần render DOCX đều thử Gotenberg rồi tự chọn Story theo tình trạng dịch vụ tại thời điểm chạy. `ProcessingConfig`/fingerprint vẫn giữ processor version cũ, `config_payload` vẫn ghi converter=pymupdf-story, không có lựa chọn converter hoặc phiên bản Gotenberg/LibreOffice. `request_run` dùng fingerprint để reuse completed run; `execute_auto`/OCR execution render lại trước persist khi chạy tiếp. Nếu job có artifact từ Story rồi chạy lại khi Gotenberg đã bật (hoặc ngược lại), dữ liệu có thể khác và `_write_artifact` trả artifact_conflict; `_sync_pages` cũng chặn render_mismatch. Job completed trước đó có thể được reuse mặc dù người dùng chờ converter mới, trừ khi yêu cầu force/generation mới. Bảo vệ bất biến ngăn ghi đè bằng chứng, nhưng khả năng tiếp tục công việc bị ảnh hưởng.

Renderer kết quả còn ghi name=gotenberg nhưng version=pymupdf.version[0], không ghi phiên bản converter thực. Khi fallback, cảnh báo nguyên nhân chỉ ở log, không được bổ sung vào warnings của kết quả. Cần ghim policy/converter/version tương ứng, quản lý generation và tái sử dụng render_pdf đã lưu khi phục hồi; không sửa hash guard để che lỗi. Suy luận từ luồng mã, chưa tái hiện runtime.

### F02 — P1: GOTENBERG_URL khai báo ở Settings nhưng renderer đọc trực tiếp os.environ

Vị trí: `backendV1/qnu/domains/ocr/artifacts/render.py:156`; `backendV1/qnu/platform/config.py:58`.

Settings đọc `.env` bằng pydantic-settings, không có bước export giá trị đó vào process environment. Renderer bỏ qua Settings và đọc os.environ, mặc định127.0.0.1:3005. Vì vậy đổi GOTENBERG_URL chỉ trong `.env` theo cách chạy V1 hiện tại sẽ không đổi endpoint renderer; URL tùy chỉnh hoặc container host có thể bị gọi sai, sau đó tự fallback khiến lỗi cấu hình khó thấy. Biến môi trường được export thật vẫn có hiệu lực, và mặc định loopback hiện tại có thể chạy bình thường. Cần truyền cấu hình đã resolve/ghim vào adapter thay vì tạo nguồn cấu hình thứ hai.

### F03 — P2: Chờ HTTP Gotenberg trong khóa render chung gây nghẽn cả PDF

Vị trí: `backendV1/qnu/domains/ocr/artifacts/render.py:159`, `:282`.

`render_async` giữ `_render_lock` quanh toàn bộ render_document; DOCX nay thực hiện HTTP đồng bộ timeout60giây bên trong. Cùng khóa được dùng bởi render PDF và extract_native_async. Nếu Gotenberg chậm, các tác vụ PDF/native khác trong cùng process cũng phải đợi dù không cần dịch vụ đó. `to_thread` giữ event loop responsive nhưng không loại bỏ nghẽn khóa. Cần tách HTTP conversion khỏi vùng khóa MuPDF, giữ khóa cho những thao tác thực sự cần serial hóa. Không khẳng định đang có nghẽn thực tế vì chưa đo/chạy.

### F04 — P2: Ghi raw response và exception Gotenberg vào log

Vị trí: `backendV1/qnu/domains/ocr/artifacts/render.py:172`.

Log ghi resp.text[:200] khi chuyển đổi không thành công và ghi exception thô khi gọi lỗi. Body lỗi của converter/gateway là dữ liệu không tin cậy; có thể chứa chi tiết nội dung tài liệu, đường dẫn hoặc URL có thông tin nhạy cảm. Giới hạn200ký tự không đảm bảo an toàn. Cần ghi mã lỗi/status/loại exception và định danh truy vết được phép; không ghi response body hoặc URL credential. Chưa quan sát log nhạy cảm thực tế.

### F05 — P2: Unit test DOCX không còn cô lập dịch vụ

Vị trí: `backendV1/tests/unit/test_ocr_render.py:79` (và ca bảng:93).

Các ca cũ gọi render_document trực tiếp mà không chặn/mock Gotenberg. Sau thay đổi, chúng phát sinh HTTP thật tới endpoint local hoặc biến môi trường. Ca paginated còn bắt buộc converter=docx-story, trái với nhánh ưu tiên Gotenberg nếu service chấp nhận fixture. Test mới chỉ mock nhánh Gotenberg thành công cho riêng ca mới, không cô lập các ca cũ. Kết quả và thời gian chạy vì thế phụ thuộc dịch vụ; có thể gửi fixture tới endpoint được cấu hình ngoài test. Cần mock riêng success/failure/config path hoặc dùng fake adapter và tách kiểm tra tích hợp thật. Không chạy các test này theo yêu cầu.

## Phần chưa thấy vấn đề qua đọc mã

- API đọc render_pdf đi qua `_scope` → resolve_workspace_access và revision scope, kiểm run theo workspace/revision, đọc artifact theo kind/page và kiểm hash qua helper hiện có. Không thấy đường đọc tùy ý blob key do client cung cấp trong endpoint mới.
- Workspace navigation kiểm workspace access trước truy vấn source, truy vấn source có workspace_id, sau đó kiểm lifecycle collection/source. Route resolve-route nằm trước route tham số workspace_id để tránh bị bắt nhầm. Chưa phát hiện bypass quyền trong phần mã đã đọc; không coi đây là chứng nhận bảo mật runtime.
- Không thấy sửa trực tiếp bytes tài liệu gốc, publication hoặc index đang phục vụ trong diff này. Tác động chính là artifact DOCX mới, reuse/retry và thông tin nguồn cho Compiler/RAG sau này; nội dung đã xuất bản không tự được tái biên soạn bởi các thay đổi đang xem.

## Kiểm chứng và bàn giao

TEST/LINT/BUILD/RUNTIME: NOT RUN, theo yêu cầu người dùng. Không gán PASS cho nhận định tĩnh. Chỉ tạo báo cáo/memory; không sửa BE/FE, config đang chạy, migration, restart, reindex hoặc push. Đề xuất xử lý F01/F02 trước, sau đó F03–F05. Trước triển khai cần đọc lại diff vì có phiên khác đang thay đổi cùng workspace.
