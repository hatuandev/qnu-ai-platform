# NHẬT KÝ LÀM VIỆC: ĐÁNH GIÁ HIỆU QUẢ TOKEN CỦA AGENT VIBE CODING

- **Thời gian**: 2026-09-19 13:49 (UTC+7)
- **Kỹ sư / Agent**: AI Senior Full-Stack Architect & Enterprise AI Systems Specialist
- **Mục tiêu**: Xác định nguyên nhân các phiên Vibe Coding tiêu tốn nhiều token và đề xuất cấu hình vận hành gọn hơn.

## 1. Kết quả audit

- `AGENTS.md` gần chạm giới hạn instruction mặc định 32 KiB.
- `PROJECT_CONTEXT.md` đã trở thành lịch sử tích lũy 709 dòng thay vì bản tóm tắt trạng thái hiện tại.
- Một phiên review rộng có thể nạp thêm khoảng 10.000 token từ bảy skill QNU.
- Cấu hình mặc định đang dùng reasoning `xhigh` cho mọi tác vụ.
- Chính sách bắt buộc đọc memory, tạo snapshot, cập nhật nhật ký và chạy kiểm tra rộng ở mọi phiên tạo thêm tool calls và context lặp lại.

## 2. Khuyến nghị

1. Rút `AGENTS.md` còn 80-120 dòng, chỉ giữ invariant và routing.
2. Rút `PROJECT_CONTEXT.md` còn 100-150 dòng; chuyển lịch sử sang snapshots nhưng không đọc lại mỗi turn.
3. Mặc định reasoning `medium`; nâng lên `high/xhigh` theo từng nhiệm vụ khó.
4. Mỗi task chỉ nạp tối đa 1-2 skill liên quan.
5. Tách Fast Mode và Full Gate; full test/log chỉ chạy tại checkpoint, commit hoặc release.
6. Mở task mới cho từng feature thay vì kéo dài một thread qua nhiều giai đoạn.

## 3. Kiểm thử

- Docs-only review; không chạy test và không thay đổi runtime/data.
