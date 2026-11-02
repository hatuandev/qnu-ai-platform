# Phiên 804 — So sánh sửa chính tả OCR bằng GPT-OSS 120B

## Phạm vi và phương pháp

Người dùng yêu cầu thử model thứ hai `ollama/gpt-oss:120b`. Dùng provider hiện có
qua ModelOps, khóa bảo vệ trong DB; không đọc/xuất khóa LLM từ .env. Không sửa mã
ứng dụng, prompt, validator, OCR, văn bản đã lưu hoặc compiler. API thử riêng ở
loopback chạy mã hiện tại, không restart API/worker/FE chính.

Đối chiếu cùng manifest802: nguồn OCR v0, cùng hash, 7 trang 1/2/15/20/27/31/32,
114 đoạn/ô, 8 nhóm, prompt `qnu.ocr.spelling/v4`, context v1 và cùng danh sách
context_evidence_ids từng nhóm. Gửi mỗi nhóm một lần bằng key mới; audit QNU ghi
8 executions, mỗi execution đúng attempt1. Không retry/salvage để làm xanh.

Provider đang active, có khóa nhưng chưa được cấp cho workspace. Cấp tạm qua API
ModelOps, giữ defaults và các grants cũ; hoàn trả đúng trạng thái trước có so sánh
concurrent drift. Không sửa cấu hình reasoning, capacity, timeout hoặc model mặc định.

## Kết quả thực chạy

**Chất lượng và hợp đồng: FAIL.** 1 completed / 7 failed / 0 uncertain / 0 NOT RUN;
không gợi ý hợp lệ được trả về hoặc lưu. Thời gian cộng request 84,32 giây,
57.927 token. Server trả alias `gpt-oss:120b` cho model yêu cầu có prefix `ollama/`.

| Nhóm | Kết quả |
|---|---|
| p15-probe | 422 chat_output_truncated |
| p01-00 | 422 chat_output_truncated |
| p02-00 | 502 ocr_spelling_invalid |
| p15-00 | 422 chat_output_truncated |
| p20-00 | 422 chat_output_truncated |
| p27-00 | 200 completed, suggestions rỗng |
| p31-00 | 422 chat_output_truncated |
| p32-00 | 502 ocr_spelling_invalid |

5 phản hồi finish_reason=length, completion_tokens=4096; bốn phản hồi content
rỗng, còn trường reasoning dài. Probe JSON bị cắt giữa chừng nên chưa thể đánh
giá model có sửa đúng `cơ bán` hay không. Không phải bằng chứng input vượt context.

2 phản hồi stop hiểu sai context_before/context_after thành prefix/suffix:
trang32 before chỉ phần trước từ, after chỉ phần sau từ, trái contract yêu cầu
cả cụm nguyên văn và cùng cụm sau sửa. Trang2 before/after chỉ ký hiệu đánh dấu.
Guard từ chối đúng; không thay guard hoặc ghép output rồi nhận PASS.

Trang32 model đề xuất `liên he → liên hệ` và `dịa chi → địa chỉ`, đều đúng sau
đối chiếu crop ảnh nguồn. Đây chỉ là dấu hiệu nhận diện lỗi, không phải batch PASS;
các mục vẫn thuộc batch failed và không được áp dụng. Trang27 mảng rỗng không
chứng minh OCR đã chính xác. Chưa CER/WER hoặc đánh giá toàn bộ 32 trang.

## Giới hạn so sánh và nguyên nhân

ModelOps GPT-OSS hiện capacity unknown/reasoning not_configured, nên dùng ngân sách
tạm 32768 context/4096 output và reasoning server default. Qwen802 dùng output16384
và thinking off đã verified. Vì vậy không xếp hạng chất lượng tiếng Việt hai model
từ lượt cấu hình khác nhau này. Bằng chứng trực tiếp chỉ ra giới hạn output/tham số
suy luận chưa xác minh và khả năng tuân hợp đồng quote là hai vấn đề cần xử lý.
Không tự đoán tham số tắt reasoning hoặc công bố capacity tạm là giới hạn server.

## Toàn vẹn, lệnh và artifact

- `backendV1/.venv/Scripts/python.exe tmp/ocr803-discover.py`: exit0, đọc cấu hình an toàn.
- Runner preflight đầu exit1 vì latest đã lên30 từ IDE khác, chưa dispatch model;
  giữ log tại tmp/ocr803/preflight-1. Sửa helper để bảo toàn latest thực tế rồi chạy
  cohort frozen raw0; không gửi lại request model nào.
- `backendV1/.venv/Scripts/python.exe tmp/ocr803-live.py`: exit0, đủ8 nhóm;
  runner kết thúc không đồng nghĩa kiểm thử chất lượng PASS.
- Helper inspect ban đầu exit1 vì console cp1252 không in được tiếng Việt;
  đặt stdout UTF-8, đọc lại stored replies, không gọi lại model. Inspect cuối exit0.
- `backendV1/.venv/Scripts/python.exe tmp/ocr803-report.py`: exit0, xác nhận8attempt1,
  cùng selection/context/prompt và tổng hợp kết quả FAIL.
- Latest text30/hash `988fe0ae8b9b5c66675dbeef43c02cde575b5c4f72d99bcd137fb19603c89c5f`
  giữ nguyên; compiler30 `cmp_f5401a18cdcf` completed/attempt1 ghim đúng version/hash;
  compiler29 cũ vẫn completed. PDF/canonical hash không đổi. Không SaveReview,
  publication hoặc indexing. Defaults/grants hoàn trả, API tạm đã đóng.
- Không sửa ứng dụng nên Pytest/Vitest/build NOT RUN; không lấy kết quả offline802
  làm PASS hiện tại. Kiểm tra JSON, liên kết mới, UTF-8/LF và diff cuối task.

Artifact `tmp/ocr803/`: report.md/json, manifest, 8receipt/response/raw, diagnostics,
provider-before, grants-before/restored, integrity-final. Tên thư mục803 giữ nguyên
vì đã tạo trước khi phát hiện IDE khác dùng số phiên803; nhật ký/snapshot dùng804.
Không ghi đè nhật ký hoặc công việc phiên803 đang tồn tại.

Hướng tiếp: xác minh reasoning/capacity GPT-OSS, đơn giản hóa contract sinh quote/
vị trí bằng thuật toán bám nguồn, rồi đo cohort mới; giữ numeric/provenance guard.
