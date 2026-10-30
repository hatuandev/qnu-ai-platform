# Phiên 730 — Phục hồi review bị timeout và kiểm lại compilation

## Yêu cầu và nguyên nhân

Người dùng yêu cầu xử lý review đang kẹt và hướng dẫn chạy lại. Giữ Qwen context/input/output262144/221184/32768 và Compiler8192. Đối chiếu API và DB chỉ đọc của review cũ: request_started01:06:44, finished01:08:44, uncertain/chat_provider_uncertain; ModelOps timeout120giây. Adapter map read timeout/request error sau gửi thành uncertain, không tự retry. Review có14source unit/13draft unit. Không kết luận model không hỗ trợ hay nguồn thiếu.

## Xử lý có phạm vi

- PATCH timeout Qwen từ120 lên300giây qua API ModelOps của E2E fe2d3c3576e6. Chỉ timeout thay đổi, không key/endpoint/capacity/quota. Không sửa backend hoặc restart/migration.
- Người dùng đã yêu cầu recovery: tạo review mới qua API, idempotency key mới, cùng run/draft/source/provider và output8192. Giữ nguyên review cũ uncertain và usage/evidence. Artifact recovery an toàn trong tmp; chỉ trỏ checkpoint sang review mới sau khi completed, không sửa status DB bằng tay.
- Review mới rvw_c70ad1ab59b0 HTTP200/completed/no_issues_detected, usage15470; request_started01:21:54 → finished01:23:38, khoảng105giây. Không coi uncertain cũ là đạt.
- `frontendV1/e2e/stages/session.ts`: cho truyền timeout riêng vào POST/JSON/raw, mặc định180000ms và token/key/body giữ nguyên.
- `frontendV1/e2e/stages/workflow.spec.ts`: trước POST review đọc timeout model đã ghim qua API; dùng timeout+30giây, thông báo bắt đầu/thời hạn thật. Không retry, không bỏ gate review. Giữ fail-fast uncertain từ729.
- `frontendV1/tests/e2e-request-timeout-730.test.ts`: ba regression về timeout mặc định, review>180s giữ body/auth/idempotency, HTTP504 không tự gửi lại. Fixture manifest tạm tổng hợp, không gọi mạng/credential thật.
- Hướng dẫn bổ sung thời hạn review. Phần resume sau tắt máy của729 giữ nguyên.

## Kiểm chứng đã chạy

- `vitest run tests/e2e-request-timeout-730.test.ts tests/v1-contract.test.ts`: exit0,17PASS/2file (3mới+14contract).
- Biome ba file source/test sửa: ban đầu FAIL format/import test; sau chỉnh exit0, không error.
- `npm run build`: exit0, Vite+tsc đạt; còn cảnh báo import extension native/chunk lớn có sẵn.
- Live model-chat sau timeout mới:1PASS HTTP200/671ms. Navigation/upload/extraction chạy lại mỗi chặng1PASS, giữ nguồn cũ.
- Compilation đang kiểm trên cả hai tài liệu: lượt review đầu dùng report completed vừa phục hồi; nguồn thứ2 biên soạn đã qua và đang review với timeout300.

## Giới hạn

Không sửa code backend nên không chạy full backend. Chưa nghiệm thu publication/chat/permissions/lifecycle sau recovery; không tự approve finding hoặc xóa nguồn. Kết quả compilation cuối bổ sung sau khi lệnh hoàn tất. Giữ diff trước phiên và không push.

## Bổ sung khi tiếp tục tại731

Compilaton730 cuối FAIL ở review tài liệu2: HTTP422/chat_output_truncated, đủ8192completiontokens đều là reasoning, content trống. Lượt phục hồi dùng structured_output đã gửi sau đó completed trong~91s, checkpoint trỏ review mới; user yêu cầu tạm dừng nên chưa nghiệm thu toàn chặng tại730. Đối chiếu731 xác nhận không còn review chạy; kết quả mới/capacity128K được ghi riêng tại731. Không xóa các lượt failed/uncertain.
