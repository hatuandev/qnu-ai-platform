# NHẬT KÝ LÀM VIỆC — Phiên #71
# Ngày: 2026-09-17 | Tiêu đề: Đồng Bộ Quản Trị Trợ Lý AI Core → Platform

## 1. Bối Cảnh & Nguyên Nhân
- Trang `/assistants` của Platform hiển thị 5 card từ hằng số frontend, không đọc API.
- Bảng PostgreSQL `assistants` có 0 dòng; service backend bắt mọi lỗi hoặc trạng thái rỗng rồi trả `STANDARD_ASSISTANTS` trong bộ nhớ nên giao diện trông như có dữ liệu thật.
- Core đã có luồng quản trị đầy đủ hơn: template, assistant, workflow draft, import/export bundle và detail cockpit.

## 2. Thay Đổi Kỹ Thuật
- Chuyển Assistant sang **DB là nguồn sự thật duy nhất**; không còn fallback mock khi DB rỗng hoặc lỗi.
- Tạo seed idempotent 5 trợ lý và 5 workflow từ `configs/workflows/*.json`; chỉ thêm bản ghi thiếu, không ghi đè dữ liệu người dùng.
- Mỗi trợ lý lưu cấu hình vòng đời 7 lớp theo chuẩn QNU: Persona/Scope, Knowledge, Model/Fallback, Guardrails, Tools/HITL, Output/Citations và Evaluation TM-08.
- Hoàn thiện API CRUD, soft-delete, template, seed, import/export `.qnu.bundle` và detail theo code hoặc ID.
- Thay giao diện tĩnh bằng ba route độc lập:
  - `/assistants`: danh sách thật, tìm kiếm/lọc, trạng thái tải/lỗi/rỗng, seed và import.
  - `/assistants/new`: cấu hình tạo mới theo vòng đời 7 bước.
  - `/assistants/:code`: chỉnh sửa metadata, model, guardrails, liên kết Knowledge/Chat/DAG và xuất bundle.
- Giữ nguyên phạm vi Provider/ModelOps của phiên đang chạy song song; Assistant chỉ lưu model ID tham chiếu, không lưu API key.

## 3. Dữ Liệu & Xác Minh Runtime
- Script seed chạy lại trả `assistants_added=0`, `workflows_added=0`, `total_assistants=5`, chứng minh idempotency và dữ liệu đã được persist.
- `GET /platform/v1alpha1/assistants`: HTTP 200, 5 bản ghi có ID ổn định.
- `GET /platform/v1alpha1/assistants/admissions`: HTTP 200, có lifecycle config đầy đủ.
- `GET /platform/v1alpha1/assistants/templates`: HTTP 200, trả 5 mẫu Core.
- Kiểm tra trình duyệt xác nhận list/detail/create render đúng dữ liệu backend.

## 4. Kết Quả Kiểm Thử
- Backend Ruff: 0 lỗi.
- Assistant tests: 7/7 passed.
- Backend full suite: 141/142 passed; lỗi duy nhất thuộc thay đổi OCR concurrent (`OCRExtractResponse` chưa có `fallback_engine`), không thuộc Assistants và không được sửa chồng trong phiên này.
- Frontend Biome: 0 lỗi trên 90 files.
- Frontend TypeScript: 0 lỗi.
- Frontend Vite build: thành công.
