# 10 — Phạm vi provider, ngân sách JSON và lỗi inference RAG

> **TÀI LIỆU LỊCH SỬ — không phải hiện trạng V1.** Nội dung dưới đây mô tả hệ thống `backend/` + `frontend/` trước V1 (hai thư mục đã gỡ khỏi checkout) và chỉ dùng để truy vết. Bản đang chạy là [`backendV1/`](../../backendV1) + [`frontendV1/`](../../frontendV1); xem [bản đồ tài liệu](../README.md).

## Chính sách máy chủ

Phiên 498 giới hạn provider nội bộ. **Phiên 501 người dùng yêu cầu mở lại việc
chọn LLM của provider khác**, thay giới hạn đó bằng cấu hình máy chủ
`configs/rag_inference_policy.json` có `"chat_provider_mode": "modelops"`.
Primary/fallback theo cấu hình trợ lý đã lưu, provider đang bật, capability và
credential ModelOps. Không tự bật provider hoặc thay model đã chọn.

Mode `allowlist` mặc định khi không có mode vẫn yêu cầu `allowed_chat_provider_ids`.
Không trộn danh sách này với mode `modelops`; thiếu/sai file, mode lạ hoặc cấu hình
mâu thuẫn phải fail-closed. Không nhận mode từ client/model. Nested scope đóng
băng cả mode `modelops` trong request và không cấp lại ngân sách retry. Các probe
phiên 501 vẫn chỉ gọi nội bộ, chặn mọi HTTP host khác.

- File được đọc từ thư mục cấu hình máy chủ qua `get_configs_dir()`, không từ request,
  prompt hoặc lịch sử. Dockerfile hiện có đã sao chép `configs/` vào image.
- Thiếu/sai file: `RAG_INFERENCE_POLICY_UNAVAILABLE`; không có route được phép:
  `RAG_PROVIDER_NOT_ALLOWED`. Không tự quay sang cloud để tiếp tục.
- `RagService.ask` cài phạm vi trước resolver hội thoại; các structured call dùng cùng
  phạm vi. ModelOps lọc route trước khi dựng adapter ở cả generate và streaming.
- Phạm vi dùng ContextVar, giữ nguyên cho một request và được trả lại khi hoàn tất,
  lỗi hoặc hủy. Không áp dụng nhầm sang request ModelOps độc lập.
- ID provider được người quản trị tin cậy; không suy mô hình nội bộ từ tên hoặc IP.
  Đổi endpoint/chức năng của provider được cho phép cần rà lại chính sách nơi gửi dữ liệu.
- Chính sách này giới hạn **LLM RAG**, không tuyên bố chặn toàn bộ OCR, embedding,
  reranker hoặc mọi kết nối mạng của ứng dụng.

## Structured JSON và repair

Giữ tối đa hai attempt logic. Lượt repair dùng ngân sách đầu ra gốc của contract,
không giảm theo độ dài JSON sai, không dùng ngưỡng 4.000/256 hoặc chars/token để
khẳng định vừa cửa sổ. Không cắt payload, quote hay điều kiện nguồn.

Khi chưa có cửa sổ/tokenizer đáng tin, provider là nơi xác nhận request mới có vừa
hay không. Đây là chính sách thực thi hữu hạn, **không phải bảo đảm trước khi gửi**.
Context overflow được ModelOps phân loại riêng, không ghi circuit/key failure.
Adapter không được tự giảm output của structured call qua context fitting; nếu không
đủ cửa sổ cho ngân sách đó thì báo lỗi thay vì tạo JSON bị cắt. Hết output vẫn là
lỗi thật; schema sai sau repair vẫn fail-closed, không tạo đáp án giả.

Không tự thêm tokenizer/model/framework, không gửi sang provider ngoài danh sách.

### Hướng dẫn đầu ra và danh tính verdict — phiên 500

Structured prompt mô tả các trường dữ liệu từ schema Pydantic thay vì nhúng cả
JSON Schema để model chép lại. Pydantic vẫn kiểm tra dữ liệu cuối; không giả định
engine hỗ trợ constrained decoding hoặc tự bật `response_format` chưa được duyệt.

Verifier và indexed audit dùng contract gắn với các claim thực của request: mỗi
ID đúng một mục, không thiếu/trùng/ID lạ. Lỗi được đưa vào lượt repair hiện có,
giữ nguyên bằng chứng và output budget. Không tự điền verdict true, gán ID theo
vị trí hoặc bỏ claim chưa kiểm tra để làm hợp đồng hợp lệ. Sai ID sau hai attempt
báo `EVIDENCE_VERIFICATION_INVALID`; vẫn giữ kiểm tra phòng vệ phía sau. Lỗi
provider/context không biến thành missing hoặc JSON repair.

Đây là giảm rủi ro qua prompt và validation, không bảo đảm model thật đã hết echo.

Phiên 501: hướng dẫn phân biệt full path root/array item. Khi model dùng `$.field`
làm tên khóa ở root, chỉ chuẩn hóa sang `field` đã khai báo cùng cấp khi không
collision. Không di chuyển trường con ra root, sửa quote/giá trị/verdict hoặc điền
trường thiếu; sau chuẩn hóa vẫn Pydantic JSON validation. Alias nested/lạ/mâu thuẫn
vẫn bị từ chối. Đây là sửa định dạng tên trường, không sửa dữ kiện.

## Chẩn đoán và retry

- Log lỗi inference chỉ gồm provider/model, stage, loại lỗi, HTTP status, reason phân
  loại và upstream request ID định dạng UUID nếu có. Không ghi raw body, quote,
  prompt, credential hoặc URL. Muốn xác nhận nguyên nhân router/engine cần log của
  máy AI; metrics `status=error` không tự chứng minh HTTP 502 hoặc OOM.
- Một ngân sách retry dùng chung trong request RAG, không cộng lại ở mỗi stage/key.
  Request ModelOps độc lập có một ngân sách riêng. Retry chỉ cho HTTP 502/503 tạm thời
  ở transport OpenAI-compatible, không cho auth/quota/400/429/schema/context.
- Chờ tối thiểu 0,1 giây; tôn trọng Retry-After dạng số khi còn thời gian. Header không
  giải nghĩa được hoặc vượt thời gian còn lại thì không retry. Lời gọi generate có
  deadline chung cho negotiation/retry theo timeout của transport.
- Streaming chỉ retry HTTP error trước nội dung; đã phát token thì báo lỗi và giữ
  phần đã phát, không nối model khác. Cancellation truyền nguyên trạng và lease
  được dọn qua ranh giới inference.
- Retry hết mà vẫn lỗi thì phân loại và failover theo route được phép; một lỗi logic
  không được đổi thành “không có dữ liệu”. Không thêm retry ở UI/runner để săn kết quả.

## Kiểm chứng và triển khai

Test bằng fake adapter/HTTP, gồm chặn cloud fallback, thiếu policy, task isolation,
budget nguyên vẹn, quote dài, context rejection, retry hữu hạn, deadline/cancellation
và streaming. Test mock không chứng minh server AI đã hết 502.

Không cần migration/reindex. Khi triển khai phải đưa cả file policy và mã mới lên
backend, rồi nạp mã theo quy trình vận hành được người dùng cho phép. Không tự
đổi provider hoặc mở cloud khi server nội bộ lỗi.
