# Phiên 972 — Kế hoạch mở rộng sản phẩm AI

Ngày 15/11/2026. Yêu cầu: lập kế hoạch chi tiết, giữ các hướng mở rộng ban đầu và hai trợ lý soạn thảo/tạo câu hỏi. Chỉ sửa tài liệu.

## Phương pháp và phạm vi

Đọc PROJECT_CONTEXT, quy định workflow/verification/UI, skill chatbot, Git status/diff stat, schema trợ lý/tác vụ/công khai, danh sách domain và sidebar hiện tại. Khảo sát tĩnh có giới hạn, không coi báo cáo lịch sử là bằng chứng runtime hiện tại.

Tạo [kế hoạch](../ke_hoach/2026-11-15_mo_rong_qnu_soan_thao_hoc_lieu_va_cong_viec.md) với P0–P6, báo cáo xuyên suốt, ranh giới dữ liệu/quyền, BE/FE, trạng thái, model, xuất tệp, kiểm chứng, rollout/rollback và backlog A01–A13. Đồng bộ mục lục kế hoạch/nhật ký, WORK_LOG, PROJECT_CONTEXT và snapshot 972. Bảo toàn thay đổi người dùng đang có.

## Kiểm chứng

- Đã đọc các file/contract nêu trên bằng Get-Content/rg và kiểm Git status/diff; exit code 0 ở các lượt khảo sát.
- PASS: script Python kiểm đường dẫn local trong ba file mới, UTF-8 không BOM/LF và marker trong các index; exit 0. Đã đọc lại tiếng Việt trong nội dung tạo.
- `git diff --check` mặc định báo CRLF trên các index/memory đang dùng CRLF, gồm cả diff có sẵn. Giữ nguyên kiểu xuống dòng các file đó để không đổi toàn file; `git -c core.whitespace=cr-at-eol diff --check -- <4 file index/memory>` PASS, exit 0. Ba file mới dùng LF.
- Test ứng dụng, live inference, migration, 100 câu G3: **NOT RUN**, không cần cho task tài liệu.
- Không restart/reindex/deploy/commit/push hoặc sửa cấu hình model.

## Giới hạn và bước tiếp

P0 phải kiểm tra sâu các khả năng tái sử dụng và chốt mẫu Word/học liệu với người duyệt. Các domain/schema mới và ngưỡng chất lượng là đề xuất, chưa tồn tại hoặc chưa được nghiệm thu. Báo cáo 970 còn Q41/G3 chưa ổn định, 971 chưa nghiệm thu production; kế hoạch không đổi kết luận đó.

Bắt đầu A01–A02 khi triển khai được giao, sau đó P1/P2 để có lát cắt tạo trợ lý → dự thảo → xuất Word trước mở rộng sang học liệu.
