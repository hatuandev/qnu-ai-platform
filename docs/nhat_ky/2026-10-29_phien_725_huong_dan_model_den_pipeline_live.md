# Phiên 725 — Nối test model QNU với toàn luồng và tổng hợp lệnh theo thứ tự

Ngày: 2026-10-29.

## Yêu cầu

Người dùng muốn sau test model tiếp tục upload và các bước khác, dùng đúng bốn model QNU làm mặc định để thử quy trình, và cần một file hướng dẫn tổng hợp. Áp dụng clean-code/ModelOps và hướng dẫn FE ở phạm vi test. Không chạy inference hoặc thay cấu hình runtime trong phiên này.

## Thay đổi

- Thêm docs/quy_trinh/V1_TEST_TOAN_LUONG_MODEL_QNU.md: hai cửa sổ lệnh, init live/config UI,13lệnh từ discovery đến lifecycle, hai lệnh gọn models rồi all, báo cáo, retry/cleanup và giới hạn.
- frontendV1/e2e/stages/live-defaults.ts: đọc profile, báo cáo model-observation và lịch sử diagnostic current; chọn đúng child provider ID theo endpoint/parent/model/capability. Chặn config thay đổi, dimension embedding khác chiều quan sát, thiếu capacity/OCR prompt budget hoặc quota thử ngoài phạm vi.
- Navigation live yêu cầu năm chặng model PASS, cấp riêng4model đã test thành default workspace E2E và đọc lại để kiểm. Không chọn model đầu tiên cùng capability. Lưu lựa chọn trong checkpoint; compile/review ưu tiên Qwen, index ưu tiên BGE; scan kiểm provider Nemotron; assistant/gateway và câu hỏi sau purge dùng hybrid_rerank với BGE reranker. Chat kiểm trace provider/rerank thực thi.
- Profile thêm test_monthly_token_limit=1.000.000. Theo yêu cầu chạy trọn quy trình live, navigation được cấp quota hữu hạn này chỉ cho workspace E2E xác minh code đúng runID nếu chưa có. Không đặt lại usage, tăng quota đã có hoặc vượt trạng thái blocked; không áp dụng dev/production. Đây là ngoại lệ có phạm vi so với hướng dẫn724 yêu cầu cấu hình quota live thủ công, đã đồng bộ tài liệu vận hành hiện tại.
- Runner yêu cầu đủ model-stage trước mọi chặng nghiệp vụ live. Rerun model làm các kết quả pipeline hết hiệu lực; rerun discovery còn làm các probe hết hiệu lực. Tài nguyên đang có không tự bị xóa/ghi đè; đổi model sau publish/index nên dùng phiên mới.
- Giữ workflow giả lập8chặng và model test5chặng riêng. Không đổi BE, credential, default toàn hệ thống hoặc capacity giả. Đồng bộ README và các hướng dẫn trước.

## Kiểm chứng thực chạy

PASS: Biome scoped3file, TypeScript tsc --noEmit -p tsconfig.e2e.json; Ruff check/format runner và offline tests; 10 unittest offline về cleanup/order/model guard/skip/invalidation.
PASS: 6 kiểm tra offline helper live-defaults bằng TypeScript transpile cùng API giả và JSON tạm: chọn đúng tested model thay vì model đầu, reject stale, dimension mismatch, OCR budget sai, parent sai và quota vượt phạm vi. Không có network/DB/write API; thư mục tạm được dọn sau kiểm tra.
PASS: AST, UTF-8 không BOM/LF, JSON profile, liên kết Markdown mới và git diff --check cuối batch.
NOT RUN: các chặng Playwright thực thi, model QNU thật, upload/reindex/cleanup/migration hoặc restart. Chưa kết luận live pipeline PASS.

## Bàn giao

Đọc hướng dẫn tổng hợp mới, tạo phiên live và cấu hình provider/key/capacity trong ModelOps. Chạy5model-test rồi navigation/upload/extraction/compilation/publication/chat/permissions/lifecycle. Nếu review finding hoặc lỗi thực tế thì dừng đúng chặng, không nới assertion/skip. PASS diagnostic chưa phải đánh giá chất lượng độc lập.
