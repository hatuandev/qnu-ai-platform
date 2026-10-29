# Context708 — Sửa chức năng kho tri thức

Ngày: 2026-10-29. Yêu cầu: upload được nhưng UI thiếu xóa; kiểm tra và sửa các thao tác kho tri thức đang dùng.

## Đã làm

Đọc context/Git/source, AGENTS và skill clean-code/backend/frontend/admin-frontend-design. Giữ các diff knowledge/navigation/provider/startup có sẵn; lưu baseline task trong artifact bỏ qua Git.

Bổ sung chung menu tài liệu ở dạng thẻ/bảng với chi tiết/tải xuống/OCR/đổi tên/di chuyển/lưu trữ/xóa theo quyền. Xóa dùng lifecycle preview/approval/receipt/restore. Tách control vòng đời kho khỏi dropdown lồng, nối ba chặng3–5 tới trang chức năng có sẵn, dùng Button để hỗ trợ bàn phím, sửa lỗi/rỗng và đếm gốc, bỏ KPI sẵn sàng không có health. Phân trang OCR, đọc nguồn deep link theo ID, reset lựa chọn đúng, hiện lỗi revision và nguyên nhân xử lý, cập nhật lịch sử queued/running. Bảo vệ di chuyển khi chưa tải được thư mục đích. Thư mục chỉ xóa khi rỗng, server kiểm lại409 để tránh che nguồn/bằng chứng.

Thử OCR thật trên tệp tổng hợp phát hiện worker mất quyền admin local. Thêm helper danh tính nền dựa trên dev gate hiện tại ở server, dùng cho OCR/Compiler/index/auto-review; không tin role trong queue, không mở quyền SSO, production hoặc identity khác. Unit kiểm7biên; API/worker kiểm admin được phép, gate tắt và membership thu hồi đều đúng. Không thêm membership hay sửa secret.

## Kiểm chứng

Backend mới5integrationPASS +7unit quyền nền/5unit folderPASS; database thử đã dọn, sentinel giữ. Trước sửa2folderFAIL và1admin-workerFAIL đúng nguyên nhân. FE mới17regression +6OCRcũ =23PASS; full cuối439PASS/49file/exit0. Build+TypeScript/Biome13file/Ruff9filePASS. Full lintFAIL29error/7warning/1info ngoài tệp sửa, log đầy đủ. Backend full ghi đủ806kết quả804PASS/2FAIL rồi kẹt teardown Windows Proactor, không có full exit bình thường (harness exit4294967295). Recovery Selector theo opt-in fixture hiện có:17PASS/2FAIL/exit1, thoát bình thường. Hai FAIL đều assertion revision0005thay vì0006 như706; DB thử đã dọn, sentinel giữ, Redis test0key.

Lượt full đầu bị dừng khi phát hiện lỗi worker để chạy lại batch cuối, không ghiPASS; DB qnu_v1_test_0fa266e3609041a6 đã dọn/sentinel giữ. Lượt cuối DB qnu_v1_test_f3fe34d7f46541aa dùng Redis test riêng, không đổi .env.

## Live

Tạo riêng kho col_265f31085d60 và tệp tổng hợp src_eb0eaef42c26. Upload/tải xuống612byte SHA256khớp, đổi tên, tạo/di chuyển thư mục, chặn xóa thư mục còn1nguồn, xóa nguồn lca_dd61ef030e42 và khôi phục lca_43201f590995. Đã lưu trữ kho thử lca_324a45007723, không purge. Kho gốc vẫn2tài liệu.

OCR đầu thất bại workspace_not_found; sau fix qua bước quyền và báo model_not_configured đúng thực tế: workspace chưa có grants/default/quota. Người dùng trả lời “Giữ cấu hình hiện tại, hoàn tất phần sửa chức năng”. Đã chốt giữ nguyên quyền dùng model, OCR mặc định và hạn mức; không áp dụng đề xuất nemotron-parse/100.000token/tháng, không chạy thêm OCR thật. Phần sửa chức năng hoàn tất, giới hạn cấu hình AI giữ nguyên như đã báo cáo.

Desktop, mobile390×844 sáng/tối đã xem; sửa header tràn ngang, documentWidth375≤390. Đã mở trang biên soạn/xuất bản/index, không chạy publish/index trên tài liệu người dùng. Không tuyên bố chất lượng pipeline AI khi chưa đủ cấu hình.

PhiênV1 không lắng nghe đầu task; preflight5mụcđạt rồi khởi động và chỉ restart process do task tạo để nạp backend/worker. API/worker/FE đang chạy bản sửa; health live/ready/FE200. Hash17file app khớp sau kiểm chứng cuối.

[Báo cáo](../bao_cao/context708/KNOWLEDGE_FIX_REPORT.md); artifact local storage/artifacts/knowledge-fix-708/. Không migration/env/grants/quota/reindex/Git commit/push ngoài phạm vi đã được chốt. Giữ lịch sử các phiên cũ.
