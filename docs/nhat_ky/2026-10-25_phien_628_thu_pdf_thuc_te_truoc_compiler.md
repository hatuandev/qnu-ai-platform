# Phiên628 — Thử PDF thực tế trước Compiler

Người dùng giao chọn một PDF, sau đó xác nhận bóc tách MD/JSON rồi chạy Compiler trên PDF mới. Dùng qnu-knowledge-ingestion, pdf và hướng dẫn ModelOps/clean-code cho harness thử; không sửa app, không chạy lại Compiler ba DOCX đã được nghiệm thu.

Chọn thông báo quy đổi điểm QNU 2026, 5 trang, SHA `96207cca90ecd30df23d9ffcf74fb982a6277e4d89b08270e3465a4a2bd5dc8e`. Lưu nguồn bằng LocalStorageDriver riêng. Native replay và cặp QNU Markdown/JSON thật PASS; xem đủ 5 trang. Đối soát giữ 760/760 vị trí raw từ grid sang fields; chưa chứng nhận ngữ nghĩa số liệu.

Luồng tự động NEEDS_ATTENTION: 7 blocker (6 vùng hình, 1 nối bảng), 760 limitations. Phụ lục1 đúng 23 cột nhưng header2 tầng chưa được nhận; Phụ lục2 phân2trang4cột cũng header_depth0. Nguyên nhân header_role_evidence đòi bold và shading trong khi header nền trắng. Công thức phân số còn tách dòng, chưa chứng minh dùng tính toán đúng. Chưa sửa parser.

Preview/create Compiler thực tế chặn source_not_current_ready, 0 LLM Compiler. Không đặt ready giả để chạy tiếp. ModelOps hiện đọc ra gh/gpt-6-luna, không thay defaults; chưa gọi model này cho PDF. Không có bundle biên soạn PDF hoàn tất.

Lượt header rescue đầu bị Redis cô lập chặn trước OCR, không phải upstream OCR FAIL. Lượt xác minh với capacity thật bị auto-review chặn egress vì chưa xác nhận payload/đích/fallback; không bypass. Read-only preview thấy Paddle nội bộ100.105.13.53:8080; chờ xác nhận rõ nếu tiếp tục chỉ crop đầu trang1, không cloud fallback.

Hai DB test có nonce sở hữu đã dọn, Storage giữ bằng chứng/policy. Hash app/source/shared domain/config rows khớp trước/sau. Không model/config/source/Quality Gate writes trong app đang dùng; không vector/pub/restart/commit/push. App/full tests NOT RUN vì không sửa mã ứng dụng; giữ kết quả Compiler cũ là lịch sử.

[Báo cáo và lệnh/exit code](../bao_cao/context628/REVIEW.md). Evidence ignored tại backend/storage/context628, gồm raw/MD/JSON/projection, audit, compiler receipt, postcheck và closeout. Harness lỗi đầu/giới hạn đã ghi rõ; chỉ báo PASS cho kiểm tra cuối thực chạy đạt, nội dung tổng thể vẫn NEEDS_ATTENTION.
