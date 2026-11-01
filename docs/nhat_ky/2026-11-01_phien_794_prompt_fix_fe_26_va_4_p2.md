# Phiên 794 — Prompt sửa 26 test FE và 4 P2 ModelOps

Ngày 01/11/2026. Người dùng yêu cầu viết prompt để tiếp tục vibe trong IDE. Phạm vi phiên này là tài liệu bàn giao, chưa triển khai các bản sửa.

## Nội dung bàn giao

- [Prompt794](../ke_hoach/PROMPT_FIX_FE_26_TEST_VA_4_P2_794.md) ghi rõ bốn P2 từ review793: catalog thiếu dữ liệu ngân sách cho consumer; Save có thể xóa declaration không xác nhận; classifier bỏ lọt mã lỗi BE thật; hiển thị sai nguồn từng giới hạn.
- Liệt kê đủ 26 test thất bại trong 8 file, đối chiếu exact file + test name với artifact793. Phân biệt test lỗi vì fixture/context với lỗi sản phẩm, không mặc định có 26 lỗi sản phẩm độc lập.
- Cho phép sửa nhỏ hợp đồng catalog/provenance BE–FE khi cần; yêu cầu regression quyền truy cập, payload submit và DOM. Không dùng skip, bỏ assertion, nới guard hoặc retry để làm xanh.
- Ghi thứ tự sửa, kiểm chứng offline, full FE gate và báo cáo trung thực full BE nếu lỗi nền716 vẫn còn. Giữ session93faa11f0caf, lịch sử benchmark và uncertain789; không restart, gọi model thật hoặc thay cấu hình live.
- Thêm mục lục kế hoạch và đồng bộ nhật ký, WORK_LOG, PROJECT_CONTEXT, snapshot794; giữ nguyên lịch sử791–793.

## Kiểm chứng

- Đối chiếu tên 26 test với `tmp/review793-failure-comparison.json`, kiểm tra liên kết local và các đường dẫn source/test trong prompt.
- Kiểm tra UTF-8 không BOM, LF và `git diff --check` trên tài liệu sửa/thêm.
- Test ứng dụng, build, visual và live inference: **NOT RUN**, vì đây là thay đổi tài liệu thuần túy theo verification của repo.
- Baseline **611 PASS/26 FAIL** và bốn P2 là kết quả lịch sử793, không phải kết quả chạy mới hoặc lỗi đã được sửa trong phiên794.

## Bước tiếp theo

Dùng toàn bộ prompt794 trong IDE để sửa và kiểm chứng. Chọn số phiên mới chưa dùng cho lượt triển khai; không ghi đè794 hoặc báo hoàn thành trước khi đạt tiêu chí trong prompt.
