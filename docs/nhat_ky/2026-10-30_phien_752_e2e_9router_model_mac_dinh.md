# Phiên 752 — Hai nhà cung cấp E2E và chọn model chat

## Phạm vi và thực hiện

Người dùng cấp endpoint `https://qnu-9router.duckdns.org/v1`, model `ollama/gpt-oss:120b`, key tự nhập. Chỉ sửa script/profile/E2E và hướng dẫn; không đổi backend runtime, cleanup/init/restart hay gọi live thiếu key.

- Bootstrap hỏi key QNU rồi key9router bằng getpass, gửi qua ModelOps local; checkpoint chỉ ID/lựa chọn. Key active tái dùng; model mặc định chọn1Qwen hoặc2GPT-OSS. Enter mặc định Qwen lần đầu hoặc lựa chọn đã lưu. Không đưa key vào .env/source/log.
- Chọn9router thì discovery/đăng ký/sync capacity. Thiếu context/output mới hỏi số token Ollama thực tế; trống hoặc sai thì dừng. Không đoán theo model hay sao chép giới hạnQwen. Model9router không được chọn có thể giữ unknown, không cấp default.
- Thêm `chatSelection`/`routerProviderSetup`; provider-setup kiểm thêm connection/key/model9router. Discovery kiểmhai endpoint, model-chat probe đúng lựa chọn; navigation giữ guard current/capability/endpoint/capacity và gắn default workspace thử. Compiler/review/chat dùng lựa chọn; OCR/embedding/rerank giữQNU. Không đổi default global/dev.
- Chặn provider-setup sau upload, gồm admissions, vì test có bật/tắt provider. Muốn đổi model thì rerun trước upload và kiểm lại các chặng sau; phiên751 có dữ liệu giữ nguyên.

## Kiểm chứng thực chạy

- Root: `backendV1/.venv/Scripts/python.exe -X utf8 -m unittest discover -s scripts -p 'test_*.py' -q`:21PASS/exit0, gồm9case bootstrap và mockHTTP tại API local; không network/model thật. Kiểm hai key đúng connection, không lộ checkpoint/output, chọnmodel/capacity, terminal không tương tác và guard sauupload.
- Lượt scripts đầu thiếu `-X utf8` có6ERROR stdout encoding Windows ở testcũ; rerun đúng wrapperUTF-8 đạt21PASS, không sửa guard để che lỗi.
- frontendV1: `npx vitest run tests/e2e-provider-selection.test.ts tests/e2e-capacity-735.test.ts tests/admissions-recovery.test.ts tests/progress-budget.test.ts`:28PASS/exit0.
- E2E TypeScript (`tsconfig.e2e.json`), Biome scoped, Ruff2script và `git diff --check`:PASS. `npm run build`:PASS(Vite+TS), cảnh báo configLoader/bundle lớn có sẵn. Không sửa generatedroutes.
- Live9router/provider-setup/model-chat/pipeline:NOT RUN, chờ user nhập key. Không tuyên bố Ollama thật/schema compiler đã verified. Gate backend lịch sử751 vẫn479PASS/1FAIL source_purge716; không chạy fullbackend cho thay đổi script/E2E.

## Bàn giao

Trên phiên live mới, giữserve cửa sổ1; cửa sổ2 chạy `./test-v1-e2e.ps1 run provider-setup --headed`, nhập hai key ẩn rồi chọn1/2. Nếu chọn9router và metadata thiếu thì nhập context/output thật. Tiếp tục discovery/chat/embedding/rerank/OCR/navigation theo [hướng dẫn](../quy_trinh/V1_TEST_TOAN_LUONG_MODEL_QNU.md). Không tự dọn phiên751 có OCR/draft/report cần giữ.
