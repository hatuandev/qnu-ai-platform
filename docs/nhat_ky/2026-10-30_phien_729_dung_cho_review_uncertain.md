# Phiên 729 — Dừng chờ khi review đã uncertain

## Yêu cầu và bằng chứng

Người dùng báo compilation lâu sau khi mở máy, đã gọi cleanup/init nhiều lần và serve báo đang chạy. Không suy tiến trình tối qua sống qua lần tắt máy. Kiểm tra hiện tại xác nhận phiên E2E fe2d3c3576e6 chưa cleaned, các cổng hạ tầng/API/FE đều mở; có serve/API/worker/FE hiện hành. Không chạy thêm serve/init/cleanup hoặc ngắt tiến trình người dùng.

API chỉ đọc xác nhận run biên soạn completed; review rvw_24d240a4c756 uncertain, error_code chat_provider_uncertain. Checkpoint giữ đúng review này. Báo cáo compilation của người dùng ghi 241863ms, expected completed/received uncertain, timeout240000ms. Nguyên nhân chờ là helper không coi uncertain là trạng thái cần dừng. Khởi tạo lại phiên không giải quyết trạng thái review và có thể xóa cấu hình thử.

## Sửa đổi

- `frontendV1/e2e/stages/session.ts`: thêm uncertain vào trạng thái dừng có error_code; giữ timeout/poll cho queued/running, không sửa backend/provider/budget/guard hoặc đổi kết quả lỗi thành PASS.
- `docs/quy_trinh/V1_TEST_TOAN_LUONG_MODEL_QNU.md`: phân biệt resume sau tắt máy với cleanup/init; chỉ bật container hiện có khi cần; giải thích uncertain không tự được retry khi chạy lại compilation.

## Kiểm chứng

- Tái hiện từ báo cáo người dùng: compilation FAIL, đợi240000ms vì uncertain.
- Sau sửa, chạy `test-v1-e2e.ps1 run compilation` trên cùng record thật: **FAIL** đúng lỗi uncertain/chat_provider_uncertain sau1.6s test, tổng runner4.1s. Không có request inference/review mới; checkpoint review có sẵn được đọc. Đây là xác nhận fail-fast, không phải toàn pipeline PASS.
- Biome ban đầu FAIL format; sau chỉnh check file session.ts exit0.
- Build+tsc đang kiểm; kết quả cuối bổ sung dưới đây.
- Các chặng publication/chat/permissions/lifecycle không chạy; không reset quota, cấu hình model/context/output8192 hoặc dữ liệu. Giữ diff trước phiên, không push.

## Cần tiếp tục

Phải chẩn đoán request review chưa rõ và chọn recovery hợp lệ trước khi tạo review mới. Không hướng dẫn chạy lặp compilation như thể sẽ gửi lại review; không tự xóa checkpoint/run hoặc bỏ review.

## Kết quả kiểm tĩnh cuối

`npm run build` tại frontendV1 exit0, Vite và TypeScript đạt. Giữ cảnh báo cấu hình native/chunk lớn có sẵn. UTF8 không BOM/LF, liên kết index729 và diff --check được kiểm sau ghi. Full backend/suite FE NOT RUN vì không đổi ứng dụng hoặc backend.
