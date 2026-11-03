# Phiên 830 — Dọn Nemotron và điều chỉnh giao diện MinerU

## Phạm vi

User yêu cầu dọn cấu hình OCR cũ và điều chỉnh ModelOps hợp lý. Áp dụng skill ModelOps, frontend và clean code. Giữ thay đổi/docs829, nguồn OCR, lịch sử, provider Qwen/BGE, key và mặc định đang dùng.

## Cấu hình thật

- Đọc connections/models/defaults/grants bằng actor development thật qua API. Đếm tham chiếu FK tới model Nemotron bằng truy vấn chỉ đọc: không có; model cũng không nằm trong defaults/grants hiện hành.
- Ghi preview `tmp/cleanup830/preview.json`, xóa duy nhất đăng ký `nemotron-parse` bằng DELETE model API (204); đổi tên connection cũ có hậu tố ID thành `Server AI QNU` (PATCH200).
- Đọc lại: connection QNU còn đúng 3 model. So toàn bộ DTO từng model còn lại bằng trước ghi; defaults/grants của 3 workspace giữ nguyên, MinerU vẫn OCR mặc định. Không sửa/xóa raw file, review/compilation/publication, usage hay key.
- Giữ adapter/parser/type lịch sử trong code để đọc kết quả cũ và hỗ trợ protocol tương thích; không còn model Nemotron trong cấu hình hoạt động/profile E2E mặc định. Không xóa dữ liệu lịch sử để xóa tên model.

## Frontend và runner

- Connection list/detail dùng giao thức thật: MinerU là Dịch vụ OCR PDF; endpoint task, không gắn `/chat/completions` hay nhãn Trò chuyện cho mọi connection. Có key chỉ nói khóa đang bật; trạng thái hoạt động dựa trên diagnostic, chưa kiểm thì hiển thị đúng.
- MinerU ẩn nhập `/models`, ẩn badge capacity LLM; giải thích PDF→task→kết quả/tokenless. Modal test mô tả PDF. Gom cấu hình model vào menu ⋯ cùng các hành động phụ.
- Bỏ code FE tự PATCH endpoint theo IP cố định/cổng 8081 và đoán Nemotron; thêm model giữ endpoint đã nhập trong ModelOps, không nuốt lỗi đổi cổng.
- Profile QNU còn chat/embedding/rerank, thêm OCR profile riêng giao thức MinerU. Python setup tạo connection đúng type, nạp key qua ModelOps bằng biến E2E QNU được phép; loại sai protocol bị chặn.
- E2E discovery không đòi MinerU trong catalog OpenAI; model-ocr chạy diagnostic PDF, không bịa HTTP200 khi adapter trả null. Navigation vẫn kiểm diagnostic current/success và đúng provider/type, nhưng không đòi capacity/prompt token LLM ở MinerU. Giữ guard các model LLM.
- Cập nhật hai hướng dẫn V1. Giữ các fixture ảnh/token OCR tổng quát ở unit test riêng, không gán lại chúng vào profile MinerU thật.

## Kiểm chứng

- Root `backendV1/.venv/Scripts/python.exe tmp/cleanup830/runtime.py --apply`: exit0, DELETE204/PATCH200/readback/cấu hình khác bất biến; receipt trong tmp.
- `node tmp/cleanup830/browser.cjs`: exit0. Trình duyệt thực localhost3001, desktop1365 và mobile390, list/detail OCR đúng task, Nemotron vắng, 0 page errors. Xem ảnh render sau chụp.
- Từ frontendV1 `npm exec -- vitest run --reporter=json --outputFile=../tmp/cleanup830/frontend-tests-final.json`: 705 PASS/0FAIL/0SKIP, exit0. Lượt trước 701PASS/4FAIL do test cũ buộc profile thật chứa OCR ảnh và đúng2connection; đã chuyển fixture tổng quát riêng, cập nhật kỳ vọng 3connection với OCR riêng, giữ assertion bảo toàn budget.
- `npm run build`: exit0, gồm tsc; chỉ cảnh báo kích thước chunk. `npm run test:e2e:typecheck`: exit0. Biome16file thay đổi PASS.
- Root unittest `test_e2e_provider_setup.py`:18PASS, exit0; Ruff hai script PASS; git diff --check PASS.
- Full backend NOT RUN vì không sửa BE module. Full live E2E/provider inference NOT RUN; browser chỉ đọc/UI, không tự tạo nguồn, gọi OCR, biên soạn hoặc hỏi model. Chưa push/restart/deploy.

## Bàn giao

Reload trang Nhà cung cấp để thấy Server AI QNU 3 model và MinerU OCR riêng. Test E2E mới sử dụng profile cập nhật; không tự cleanup phiên cũ vì có dữ liệu/report. Artefact `tmp/cleanup830/`, không đưa ảnh hoặc corpus vào Git.
