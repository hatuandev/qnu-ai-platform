# Phiên568 — Luna chính, Qwen dự phòng; benchmark chỉ Luna

## Yêu cầu và phạm vi

Người dùng cho phép đổi mô hình chính sang Luna, dự phòng sang Qwen, chạy đúng bộ64 câu bằng riêng Luna và báo cáo; không sửa code. Giữ source/index/gold/rubric/prompt và các tham số khác. Không reindex, xuất bản lại, restart, deploy, commit/push.

Sử dụng qnu-modelops-resilience và qnu-rag-evaluation. Không agent phụ, không gọi thêm model để chấm hay smoke test. Không chạy full Pytest cho thay cấu hình; full Context567 là lịch sử, không gọi currentPASS.

## Cấu hình và kiểm tra trước chạy

Xác minh development, DB/MinIO/Qdrant loopback; truy vấn preflight READ ONLY. API backend local đang chạy dùng actor development hiện hành có quyền. Chụp config/hash trước thay; mã ứng dụng khớp manifest của benchmark Qwen cuối Context567. Chụp hash1275file app/tests/scripts/frontend source để kiểm không thay code.

Đổi qua API hiện có, không SQL ghi trực tiếp:

- System chat defaults/chain: `cx/gpt-6-luna`/9router trước, `qwen3.5-9b`/QNUvLLM sau.
- Admissions model_policy: primary Luna/provider9router, fallback Qwen/providerQNUvLLM.
- Giữ temperature0,2, max_tokens5000, thinking_budget0; config khác nguyên vẹn. Đọc lại session DB mới xác nhận chỉ `system_model_defaults` và `ast_admissions` đổi đúng phần model. Provider credential không đổi.

Cấu hình này giữ sau benchmark theo yêu cầu, không khôi phục Qwen chính.

## Cách bảo đảm chỉ Luna

Runner ignored trong tiến trình riêng gọi production FastAPI handler qua ASGITransport, không dependency override/fake response và không chạy lifespan auto-seed/migration. Tận dụng server-owned inference policy hiện có, lấy giao với policy được cấu hình rồi hạn chế chat provider còn đúng9router/Luna trong request context. Không sửa policy dùng chung, không tắt Qwen provider hoặc embedding/reranker.

Khác baseline Qwen TCP về transport/process; ghi rõ giới hạn khi so latency. Không tuyên bố benchmark TCP local hoặc production E2E.

Frozen gold SHA256 `44f56799e5a07ccba7e8711c1a1cd66e99beec18a60458e1ee509cde2167d235`,64records gồm60tri thức+4social. Giữ nguồn `ks_rev_ca1e7f16d9e0`/index `idx_rev_967891af9d5d`/generation `vg_a6e3190d11af`,262chunks/368facts/262vectorpoints. Kiểm hash code, source/config và generation trong lượt, payload seals trước/sau. Không retry case uncertain, không fix lỗi đọc được rồi chạy lại.

## Kết quả

Luna đạt **51/60=85%**, bằng Qwen Context567. Câu có đáp án43/50=86% (Qwen44/50=88%); negative8/10=80% (Qwen7/10=70%); social4/4ngoài mẫu số.111usage success gpt-6-luna,0Qwenchat/0fallback, prompt467903/completion20519/maxprompt10612;64/64HTTP200,79/79citationcanonicalvalid. Runner/scorer/cleanup/finalaudit exit0. Không có chứng cứ Luna tốt hơn tổng thể từ một lượt.

FAIL→PASS: P03/P11/P15/X09; PASS→FAIL: N19/M05/P10/P16. Còn9FAIL N19/M05/P06/P07/P08/P10/P16/X05/X08. Không fix bất kỳ lỗi nào hoặc chạy lại case. P50/P95knowledge Luna532,04/33349,57ms, Qwen676,83/21464,47ms; transport/process khác nhau nên không quy toàn chênh lệch cho model.

Hash1275file mã giữ nguyên; source/config/index/generation/payload seals giữ sau đúng2configrecords được phép. PrimaryLuna/fallbackQwen đọc lại API/DB đúng, giữ sau benchmark. Dọn58threads/14gaps,0testthreads/messages/gaps còn, dữ liệu cũ/usage audit giữ. Không tạo testDB/runtimeStorage; không thử dọn runtime567 đã bị policy chặn.

ASGI process có14warning `charmap` khi log gap tiếng Việt sau commit;14record đã dọn và kiểm,64responses hoàn tất. Ghi nhận giới hạn observability, không sửa encoding/app rồi chạy lại. FullPytest/Ruff/FEbuild/holdout/concurrency/SLA/production NOTRUN; full5672785PASS/18FAIL/17SKIP là lịch sử.

## Bằng chứng và lệnh

Từ repo root, interpreter venv sẵn có:

```powershell
backend/.venv/Scripts/python.exe backend/storage/context568/inspect_config.py
backend/.venv/Scripts/python.exe backend/storage/context568/change_config.py
backend/.venv/Scripts/python.exe backend/storage/context568/prepare_run.py
backend/.venv/Scripts/python.exe backend/storage/context568/run.py
backend/.venv/Scripts/python.exe backend/storage/context568/score.py
backend/.venv/Scripts/python.exe backend/storage/context568/verify_cleanup.py
backend/.venv/Scripts/python.exe backend/storage/context568/final_audit.py
```

Preflight đầu có lỗi helper đọc sai tên field endpoint, chưa ghi dữ liệu và chưa gọi model; sửa riêng helper ignored và chạy lại thành công. Không sửa app để chạy test. Private receipts ignored dưới `backend/storage/context568/`; không ghi credential/corpus/prompt riêng vào docs.

Báo cáo: [BENCHMARK_REPORT](../bao_cao/context568/BENCHMARK_REPORT.md), [CASE_COMPARISON](../bao_cao/context568/CASE_COMPARISON.md).
