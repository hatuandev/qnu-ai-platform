# Phiên 728 — Lưu capacity và chạy model/pipeline live

## Phạm vi được giao

Người dùng yêu cầu lưu các giới hạn model đã cung cấp để test trên phiên E2E live đang có. Chỉ thay ModelOps DB của phiên `fe2d3c3576e6`; giữ endpoint, khóa được bảo vệ, dữ liệu dev và các diff trước đó. Capacity là khai báo vận hành, không phải phép đo giới hạn tối đa của upstream.

Người dùng sau đó xác nhận cho điều chỉnh budget Compiler và restart riêng E2E. Chỉ dẫn cuối thay thế mức hạ tạm 4096: giữ Compiler yêu cầu 8192; Qwen context 262144, input 221184, output 32768.

## Cấu hình và căn cứ OCR

- Đã lưu ban đầu qua API: Qwen context/input/output 131072/126976/4096; BGE-M3 input/context 8192, dimension 1024; reranker context 8192, input 1024; Nemotron context 16384, output 8192. Không tự khai báo input chưa có căn cứ.
- Request ảnh không chứng minh capacity. Phản hồi do người dùng gửi sau đó có input 2758, output 1319, total 4077, finish stop, model Nemotron và fingerprint vLLM 0.32.0. Đây là số đo một request, không tự là cận trên mọi ảnh.
- Đo ba ảnh tổng hợp bằng adapter payload/prompt hiện hành, output chỉ 1 token: 1664×2048 → input 3336; 1664×128 → 216; 128×2048 → 264. Cả ba HTTP 200; finish length là dự kiến của phép đo token, không phải nghiệm thu chất lượng OCR.
- Đối chiếu [processor NVIDIA](https://huggingface.co/nvidia/Nemotron-3.5-Parse/blob/main/hf_nemotron_parse_processor.py) và [plugin vLLM NVIDIA](https://huggingface.co/nvidia/Nemotron-3.5-Parse/blob/main/vllm_tied_patch/vllm_radio_mbart_prefix.py): pad theo grid cao16/rộng64; token thị giác theo patch16 và compression4, cộng token đặc biệt. Các số đo cùng overhead prompt khớp công thức ceil(h/16)×ceil(w/64)+8 trong cấu hình quan sát.
- Đã lưu ngân sách bảo thủ input 4096, envelope rộng1664/cao2048 và SHA-256 prompt hiện hành qua API. 4096 có dư760 so với ảnh tối đa đo3336; đây là budget cho cấu hình/prompt này, không phải giá trị mặc định chung. Đổi processor/template/server phải đo và khai báo lại. Không lưu ảnh/Base64/nội dung OCR/credential vào journal.
- Phép đo dùng credential giải mã chỉ trong bộ nhớ từ ModelOps của DB E2E được xác thực, không thêm key vào env. Artifact quan sát an toàn lưu trong thư mục tmp phiên thử.

## Sửa test và kiểm chứng

`frontendV1/e2e/stages/workflow.spec.ts`: navigation trước đây assert `granted.defaults`, nhưng API GET allowed-providers trả `providers[].default_capabilities`. Sửa đọc đúng contract, vẫn kiểm đúng tập provider, tất cả active và mapping default đủ bốn capability. Không đổi backend hoặc bỏ assertion quyền/capacity.

Đã chạy tại root:

- model-chat, model-embedding, model-rerank, model-ocr ban đầu: mỗi chặng 1 PASS; embedding quan sát1024.
- navigation ban đầu BLOCKED thiếu OCR budget; sau lưu OCR, model-ocr 1 PASS (HTTP200/93ms).
- navigation gặp assertion sai contract; sau sửa 1 PASS.
- upload 1 PASS; extraction 1 PASS.
- compilation lần đầu HTTP422/model_output_limit_exceeded do yêu cầu8192 > output khai báo4096.
- Sau được phép hạ tạm và restart, compilation dùng4096 FAIL/chat_output_truncated; run lỗi được giữ lại, chưa coi pipeline PASS.
- Biome file spec: exit0. `npm run build` tại frontendV1: exit0, gồm tsc; còn cảnh báo import extension native và chunk lớn có sẵn.

## Trạng thái tiếp tục

Đang áp dụng cập nhật Qwen mới và trả Compiler8192. Phát hiện năm container E2E cũ Exited255 trong lúc restart; đã `compose start` đúng project, giữ volume, không cleanup/recreate. Một lần chạy nền lỗi UnicodeEncodeError, sau đó PermissionError; phục hồi có kiểm tra lease/cổng. Không suy nguyên nhân dừng Docker khi chưa có bằng chứng.

Publication/chat/permissions/lifecycle sau cấu hình mới chưa nghiệm thu. Không tăng quota hoặc sửa scope, không push. Các kết quả/giới hạn cuối được bổ sung bên dưới sau kiểm tra thực tế.

## Cập nhật theo chỉ dẫn cuối của người dùng

- Đã PATCH Qwen qua API và đọc response xác nhận context/input/output **262144/221184/32768**. Giữ model/endpoint/key và giới hạn của ba model còn lại.
- `COMPILER_MAX_OUTPUT_TOKENS` trong private-env phiên E2E đã trả **8192**, đúng yêu cầu cuối. Chỉ thay một trường; không chép private-env vào Git. API/worker/FE phiên thử khởi động lại, OpenAPI/frontend HTTP200, lease serve còn chạy.
- Container hạ tầng được `compose start` lại đúng project sau Exited255; giữ container/volume/DB. Không chạy cleanup hoặc init phiên mới. Alembic startup chỉ xác nhận head đang có, không có migration mới.
- `model-chat` sau capacity mới: 1 PASS, HTTP200/938ms. Chạy lại navigation, upload, extraction: mỗi chặng 1 PASS; dùng lại nguồn đã tạo, không upload corpus riêng.
- Run biên soạn4096 failed/chat_output_truncated vẫn tồn tại. Tạo run mới qua API với idempotency key riêng, cùng nguồn/text revision và provider đã chọn; checkpoint trỏ run mới, bản ghi recovery an toàn lưu tmp. Không sửa lỗi cũ thành PASS hoặc xóa evidence.
- Compilation8192 đang chạy; các chặng sau chưa chạy. Cần đối chiếu kết quả cuối trước nghiệm thu.

## Kết quả cuối phiên

- Qwen capacity cuối: **context262144/input221184/output32768**; Compiler request **8192**. Đối chiếu DB chỉ đọc của run mới xác nhận `config.max_output_tokens=8192`, status completed, error_code null. Capacity không bị đổi để né guard.
- Test compilation cuối: **FAIL**, exit1, run report `compilation-1793322348058336000`. Đã qua đợi biên soạn, draft có paragraph và citation đúng source; POST review HTTP504/**chat_provider_uncertain**. Không tự gửi lại request chưa rõ kết quả, không approve/publish khi review chưa đạt.
- Các probe model hiện có đạt; sau lần đổi Qwen cuối, chat/navigation/upload/extraction mỗi chặng1PASS. Toàn pipeline chưa PASS. Publication/chat/permissions/lifecycle sau cấu hình mới **NOT RUN** vì compilation chưa đạt.
- Phiên E2E giữ chạy bằng serve nền có log trong tmp; giữ toàn bộ nguồn, run lỗi4096 và run8192 đã hoàn thành. Không cleanup, không đổi quota, không push. Cần kiểm tra review/provider timeout và trạng thái request chưa rõ trước khi chạy lại, không sửa guard hoặc tự coi failed là đạt.
- UTF8/LF và liên kết728 đã kiểm đạt; diff --check file chỉnh đạt. Không chạy thêm full backend/test/build sau thay đổi cấu hình; kiểm chứng mã spec là live navigation và build+tsc/Biome đã nêu.
