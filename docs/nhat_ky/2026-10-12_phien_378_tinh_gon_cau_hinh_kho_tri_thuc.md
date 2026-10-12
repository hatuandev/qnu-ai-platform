# Phiên #378 — Tinh gọn cấu hình kho tri thức

- Ngày: 2026-10-12.
- Yêu cầu đã thống nhất: bỏ tab Cấu hình, model dưới counter, chọn Embedding khi tạo kho, OCR tự động, đổi model không thay ngay chỉ mục phục vụ.
- Skills frontend/admin-design/clean-code: tái sử dụng primitives, phân biệt trạng thái phục vụ/cấu hình, thay đổi FE có phạm vi; kiểm tra build thay vì chạy Backend tests.

## Thay đổi

- `collection-header.tsx`: nút Sửa, model strip dưới counter; giữ duy nhất bộ đếm nguồn/vector của trang chi tiết.
- `collection-detail-page.tsx`: ba tab Nguồn/Dữ liệu số/Hoạt động; chuyển Sửa thông tin vào dialog. Link cũ `?tab=models` mở Sửa, không tab rỗng.
- Xóa `collection-models-tab.tsx`: bỏ form lớn và bộ đếm legacy 0 tệp/0 chunks, không để component tab vừa thay thế thành code chết. Không xóa dialog legacy khác ngoài phạm vi.
- Mới `collection-edit-dialog.tsx`: tên/mô tả, code chỉ đọc; không gửi cấu hình model, giữ pending/error/invalidation.
- Mới `collection-model-strip.tsx`: model/provider/bản active, OCR tự động từ ModelOps, origin máy chủ trong disclosure. Kho chưa có generation thì lưu Embedding mặc định (kiểm tra lại generation trước khi lưu); đã có generation thì mở luồng chỉ mục mới cho các nguồn active/Markdown ready. Không sửa pointer xuất bản tự động.
- Mới `embedding-model-select.tsx`: chọn model/provider/dimension chung, các lựa chọn thật từ ModelOps; không API key/model hardcode.
- `knowledge-page.tsx`: tạo kho bắt chọn Embedding hợp lệ, điền sẵn default ModelOps, lưu `data_processing`; OCR `auto` và rescue bật. OCR nâng cao ở Nạp tài liệu/Studio; không thêm lựa chọn OCR per-kho chưa được runtime dùng. Hủy tạo mới bỏ thay đổi form.
- `vector-load-controls.tsx`: ưu tiên cấu hình Embedding của kho thay vì luôn mặc định hệ thống; Đổi model ưu tiên lựa chọn chỉ mục mới, giữ các bước nạp/xuất bản hiện có. Guard chờ cấu hình/lỗi, nhãn dài wrap theo viewport.
- `types/knowledge.ts`: bổ sung OCR auto/PaddleOCR vào kiểu profile hiển thị.

## Kiểm chứng

- Biome 8 file chỉnh sửa đạt; Vite build + TypeScript gate cuối exit 0.
- Browser read-only trên localhost: kho tuyển sinh có 3 nguồn/3 published/145 chunks; BGE-M3/provider server AI/Bản 1 dưới counter, ba tab. Sửa mở metadata-only; Đổi model mở Chỉ mục mới cho 3 Markdown, nút Xuất bản khóa trước build.
- Form tạo kho mở được, Embedding default server AI/1024 chiều, OCR tự động PaddleOCR-VL, chọn Cloudflare được. Không nhập tên/tạo kho/lưu/nạp/xuất bản/đổi server.
- Kiểm tra screenshot desktop form tạo mới và trang chi tiết; chưa kiểm tra viewport mobile/dark hay submit tạo kho/đổi model end-to-end. Không tuyên bố E2E mutation đã đạt.
- Không Backend tests/Ruff (FE-only), không migration/reset/restart/qnu-sso/key edits. Luồng worker/ingestion/vector DB không sửa.

## Lưu ý

- OCR tự động dùng cấu hình ModelOps runtime; không coi `ocr_profile` legacy hay default trong form là lựa chọn engine bắt buộc cho mọi tài liệu.
- Guard FE khi đổi mặc định là kiểm tra UX, không thay thế khóa giao dịch BE; chỉ cấu hình lần nạp tương lai, không cập nhật generation/pointer đang phục vụ.
- Các bộ đếm legacy của trang danh sách kho vẫn thuộc API cũ, chưa đồng bộ trong phiên này; bộ đếm trang chi tiết là dữ liệu nguồn/chỉ mục hiện hành.
