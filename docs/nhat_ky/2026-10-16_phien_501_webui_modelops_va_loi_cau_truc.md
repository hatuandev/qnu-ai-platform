# Phiên 501 — WebUI, provider và lỗi cấu trúc model

Ngày 2026-10-16. Người dùng yêu cầu tìm lỗi WebUI và mở lại lựa chọn LLM provider
khác. Yêu cầu mới thay giới hạn nội bộ498; không tự chọn/bật provider, đổi model
đã lưu hoặc gửi tài liệu sang cloud khi kiểm tra. Dùng hướng dẫn Backend/RAG/
ModelOps và Frontend/admin design; tái dùng Field/Button/OptionSelect/tokens.

## Chứng cứ

- DB hiện lưu primary qwen3.5-9b / prov_rtx5090_vllm, fallback Cloudflare,
  max_tokens 8000. Chọn Cloudflare trong form chưa làm model DB thay đổi.
- Policy server cũ chỉ cho provider nội bộ nhưng UI lấy nhiều provider.
- Probe câu phương thức xét tuyển thực chạy nội bộ: SourceAnswerAudit có
  `essential_conditions` sai cấp trong claims[0], thiếu complete cấp root.
- Probe sau hướng dẫn full path: VisibleAnswerAudit dùng `$.field` làm tên khóa.
  Đây là lỗi cấu trúc đầu ra, không chứng minh tài liệu thiếu hay router HTTP502.

Lần live đầu chưa xác minh DB bị công cụ an toàn từ chối, không thực thi. Sau đó
đọc hostname provider, xác minh 100.105.13.53 và đặt guard chặn mọi HTTP host khác
trong probe, cùng allowlist riêng nội bộ và fallback=None. Không gửi cloud.

## Mã sửa

- `configs/rag_inference_policy.json`: mode modelops theo yêu cầu mới.
- `modelops/services/inference_policy.py`: mode server, giữ allowlist tương thích;
  thiếu/sai/mâu thuẫn policy fail-closed. Scope active riêng để nested calls không
  đọc lại policy hoặc cấp lại retry. Giữ provider disabled/capability/credential/
  quyền và egress; routing vẫn chọn cặp primary/fallback đã cấu hình.
- `rag/evidence_contracts.py`, `evidence_model.py`: full path root/item; chuẩn hóa
  duy nhất alias $.field cấp root khi đúng schema và không collision. Không đổi
  giá trị, quote, verdict hoặc di chuyển/điền trường. Vẫn JSON validation và2attempt.
- `assistant-model-section.tsx`, `assistant-detail-page.tsx`, `model-policy-state.ts`:
  báo chưa lưu, hiện model chính đã lưu và nút lưu gần lựa chọn; nêu tác động gửi
  dữ liệu tới provider ngoài. Không tự lưu draft.
- `model-options.ts`: ưu tiên probe_role metadata để lọc chat/reranker, không suy
  bằng tên model. CF legacy trong DB chưa có specs/capabilities: chưa tự phân loại
  lại các model cũ hoặc sửa DB; cần quản trị khai báo role qua ModelOps.

## Kiểm tra thực chạy

- Trước sửa: 6FAIL/3PASS; 5 failure đúng policy/guide, 1 lỗi fixture response thiếu
  latency đã đổi sang LLMGenerateResponse thật.
- Focus cuối **133PASS**, 5,63s; Ruff scoped **PASS**.
- Full cuối **1829PASS/11FAIL/17SKIP**, 201,78s, exit1: tổng **FAIL**. Exact IDs trùng
  `backend/storage/contracts500-full.xml`; danh sách 11 ID tại nhật ký500 giữ nguyên.
  Artifact `backend/storage/webui501-verified-full.xml`. Một lần full trước đã dừng
  khi live lộ lỗi alias cần sửa, không tính lần dừng là PASS.
- FE **7 tests PASS** (model-options/model-policy-state), Biome scoped PASS.
  Build production gồm Vite+TypeScript **PASS**, exit0; hai fixture TS trước sai import đuôi .ts/
  thiếu trường provider đã sửa, không nới compiler.
- UI desktop/light: chọn CF trong draft hiện cảnh báo chưa lưu và model đã lưu
  qwen; không bấm lưu/chat, reload bỏ draft. Screenshot
  `backend/storage/ui501-unsaved-model.png`. Mobile/dark/live cloud NOT RUN.

Lệnh trong backend (basetemp riêng UUID):

```powershell
.\.venv\Scripts\python.exe -m pytest tests/test_rag_webui_501.py tests/test_evidence_contracts_500.py tests/test_rag_inference_safety_498.py tests/test_evidence_claims.py tests/test_evidence_quality_444.py tests/test_historical_reference_449.py -q --tb=short -p no:cacheprovider --basetemp $temp501
.\.venv\Scripts\ruff.exe check app/modules/modelops/services/inference_policy.py app/modules/rag/evidence_contracts.py app/modules/rag/evidence_model.py tests/test_rag_webui_501.py tests/test_evidence_contracts_500.py
.\.venv\Scripts\python.exe -m pytest -q --tb=short -p no:cacheprovider --basetemp $full501 --junitxml=storage/webui501-verified-full.xml
```

Lệnh trong frontend:

```powershell
node --experimental-strip-types --import ./src/app/auth/test-loader.mjs --test src/features/assistants/model-options.test.ts src/features/assistants/model-policy-state.test.ts
npm exec -- biome check --line-ending=lf src/features/assistants/model-options.ts src/features/assistants/model-options.test.ts src/features/assistants/model-policy-state.ts src/features/assistants/model-policy-state.test.ts src/features/assistants/assistant-detail-page.tsx src/components/assistants/sections/assistant-model-section.tsx
npm run build
```

## Live: chưa nghiệm thu câu hỏi

Giữ cả3 kết quả, không chọn lần đẹp: trước sửa sai nesting; sau full path sai tên
khóa root; sau chuẩn hóa alias không lỗi contract nhưng **insufficient_context,
0citation, không decision status**. Lượt cuối chưa trả lời đạt yêu cầu. Không kết
luận thiếu dữ liệu, không nới guard hoặc thay model để làm xanh; cần truy tiếp
nhánh candidate/refusal/scope của lượt thiếu ngữ cảnh. Không benchmark10/20/82.

Không sửa nguồn/vector/publication, migration/reindex/restart/deploy/commit/push.
Có đổi policy file theo yêu cầu mới, được đọc theo request nên không cần restart
riêng để nạp policy. Không bảo đảm server khác đã nhận code nếu chưa deploy.
