# Context705 — Review kiểm tra API Key/kết nối

Ngày: 2026-10-29. Người dùng yêu cầu dừng nghiên cứu AnythingLLM và kiểm trang provider
local; sau đó xác nhận phạm vi **Kiểm tra API Key / kết nối**. Kết luận CHANGES REQUESTED.

## Thực hiện

Đọc context/Git/diff và source FE/BE hiện có. Dùng qnu-modelops-resilience và computer-use.
Browser Edge không có connector; inventory cho thấy IAB khả dụng nên mở trang local
bằng IAB, không điều khiển phiên Chrome của người dùng. Bấm các nút kiểm tra, đọc API
thật qua cầu nối đăng nhập local (token chỉ trong bộ nhớ), chỉ dùng mẫu có sẵn/GET models.
Không mở secret, không chạy inference/tài liệu nội bộ hay sửa cấu hình.

## Phát hiện

[Báo cáo đầy đủ](../bao_cao/context705/PROVIDER_CONNECTION_REVIEW.md) gồm9nhóm:
F1khóa riêng không chọn đúng khóa; F2“lần lượt” chỉ gọi1lượt; F3HTTP lỗi/schema sai
vẫnok; F4TLS verification tắt; F5timeout cố định10giây thay vì120giây cấu hình;
F6RoundRobin chỉ state local; F7badge active cố định; F8không lưu/cập nhật kết quả;
F9nhánh test không kiểm connection đã tắt, không nhất quán với diagnostics.

Kết nối thật trả200/ok/4model/47ms; browser test all toast31ms. Gửi key_id thứ2trả422.
Trước/sau test last_probe_at giữ nguyên. Server thật từ chối noauth và invalid-key401;
không kết luận server bỏ auth hoặc hai khóa cùng secret từ masked hint.

## Kiểm chứng

- FE `npm test -- tests/test_connection_review_705.test.tsx tests/test_provider_connections_702.test.tsx`:
  FAIL/exit1,4probe mới FAIL và4test hiện có PASS.
- Backend `uv run --frozen --extra dev pytest tests/unit/test_connection_review_705.py -q --basetemp=../storage/artifacts/provider-connection-review-705/pytest-temp-final`:
  FAIL/exit1,8probe FAIL/3control PASS. HTTP router riêng, fake session/key/upstream;
  không tạo DB test hoặc chạy migration. Có lượt shell đầu trả0do lệnh đọc log cuối;
  lượt final lưu pytest exit1đúng. Các kết quả FAIL là lỗi cần sửa, không đổi assertion.
- Ruff check/format và Biome test mới: PASS. Đã sửa lint thuộc test mới, không sửa app.
- Hash4tệp ứng dụng trọng tâm trước/sau: giữ nguyên.
- Full suite/build/benchmark/model inference: NOT RUN; review không sửa hành vi ứng dụng.
- Artifact local bị Git bỏ qua: `storage/artifacts/provider-connection-review-705/`.

## Tệp thay đổi

Thêm test BE `backendV1/tests/unit/test_connection_review_705.py`, test FE
`frontendV1/tests/test_connection_review_705.test.tsx`, báo cáo, nhật ký/snapshot và3index.
Giữ toàn bộ sửa đổi đồng thời của người dùng. Không chỉnh key/model/provider/.env,
không restart/reindex/publish/deploy/commit/push. Chưa triển khai bản sửa.
