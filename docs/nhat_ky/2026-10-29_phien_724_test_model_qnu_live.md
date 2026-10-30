# Phiên 724 — Bổ sung test model QNU thật sau khi đăng ký ModelOps

Ngày: 2026-10-29.

## Yêu cầu và phạm vi

Người dùng báo permissions/lifecycle đã PASS sau các chặng trước, rồi yêu cầu thêm test cho model từ catalog server QNU. Model mong đợi: bge-m3 (embedding), bge-reranker-v2-m3 (rerank), qwen3.8-27b-q4 (chat), nemotron-parse (OCR). Các kết quả tám chặng workflow là báo cáo người dùng, không phải một lần chạy độc lập của agent.

Áp dụng qnu-clean-code-architect, qnu-modelops-resilience và hướng dẫn FE liên quan cho bộ mã test. Không lưu credential được cung cấp trong source/docs/.env/CLI. Key sử dụng qua ModelOps DB mã hóa của phiên live; không sao chép credential từ dev hoặc tự đăng ký provider/key qua API trong phiên này.

## Thay đổi

- scripts/e2e_profiles/qnu-server.json: profile công khai không secret, endpoint QNU và bốn model ID mong đợi.
- scripts/v1_e2e_session.py: nhóm model-discovery/model-chat/model-embedding/model-rerank/model-ocr, command models; chỉ live, discovery prerequisite cho các probe độc lập, giữ riêng kết quả khỏi tám chặng nghiệp vụ. Không ghi PASS cho skip/không có bài test.
- frontendV1/e2e/stages/models.spec.ts: chọn đúng một connection đang bật theo endpoint, cần key active; model child đúng ID/capability/parent. Dùng discovery/probe API ModelOps hiện có, gửi sample tự sinh qua adapter thật. Kiểm outcome/code/upstreamHTTP/schema được adapter xác nhận và lịch sử current; dimension/usage giữ unknown nếu không quan sát được, không giả thông số phần cứng hay tự sửa dimension DB.
- Chỉ cần HTTP200 ở API quản trị chưa đủ PASS vì diagnostic có thể mô tả upstream lỗi. Kiểm requested/observed model khi upstream có trả, ghi model-observation.json an toàn sau khi đạt. Tắt trace/video/screenshot cho nhóm model.
- Playwright config chọn đúng một spec theo nhóm chặng, tránh import nhầm workflow khi chạy model. Tám chặng nghiệp vụ và command all giữ phạm vi cũ.
- Thêm docs/quy_trinh/V1_TEST_MODEL_QNU.md, liên kết ở index/hướng dẫn E2E/README test; quy trình init --mode live → cấu hình UI → chạy từng lệnh hoặc models. Các diagnostic không thay thế RAG/strict JSON/quality benchmark.
- Ba regression offline mới trong scripts/test_v1_e2e_cleanup.py: workflow bị chặn, thiếu discovery bị chặn, probe độc lập/skip không thành PASS; mock execution chỉ trong TemporaryDirectory.

## Kiểm chứng đã chạy

PASS: Ruff check/format trên runner và test; Biome scoped hai file TS/config; TypeScript tsc --noEmit -p tsconfig.e2e.json; help command nhận nhóm lệnh mới.
PASS: 9 unittest offline (bao gồm6cleanup cũ và3guard nhóm model), 0failure. Các log PASS/FAIL của subprocess giả chỉ kiểm bookkeeping, không phải kết quả model.
PASS: Playwright --list cho model-chat và navigation trong manifest tạm, mỗi lượt liệt kê đúng1test/1file; không mở trình duyệt/API/inference. AST/UTF-8/LF, JSON profile/link và git diff --check cuối batch.
NOT RUN: live discovery/probes server AI, browser E2E thực thi, Docker/init/serve/cleanup, migration hay upload. Không có kết quả upstream thực tế mới để kết luận model hoạt động.

## Bàn giao và giới hạn

Người dùng Ctrl+C/cleanup phiên workflow cũ nếu còn; init --mode live rồi serve. Mở đúng FE thử để tạo QNU provider, thêm key qua form và bốn child model; chạy model-discovery trước bốn probe. Cần quota/grant/capacity cho pipeline live tiếp theo, không lấy thông số mock làm căn cứ. Probe chỉ sample nhỏ, không chứng minh chất lượng OCR/LLM/rerank hay khả năng chịu tải. Không sửa BE/hạ tầng/dev đang chạy, không restart/push.
