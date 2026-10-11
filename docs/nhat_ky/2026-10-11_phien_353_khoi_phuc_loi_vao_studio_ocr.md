# Phiên #353 — Khôi phục lối vào Studio OCR và hiệu đính

## Mục tiêu và đối chiếu nhánh

Đối chiếu `codex/main-before-knowledge-publishing-v2-20261009` mà không checkout hoặc ghi đè worktree. Studio cũ vẫn còn các component Canvas/Toolbar/Inspector: trái xem ảnh/khung, phải Markdown và thực thể. Nút Studio OCR hiện điều hướng giống Chi tiết, không bật Studio; chế độ sửa Markdown khai báo nhưng chưa có điều khiển/textarea.

## Thay đổi

- `frontend/src/components/knowledge/tabs/collection-bindings-tab.tsx`: Studio mở nguồn với `view=studio`, Chi tiết mở chế độ thường.
- `frontend/src/routes/knowledge.$collectionId_.sources.$sourceId.tsx`: validate search view/revision và điều phối chế độ qua URL, F5 giữ Studio.
- `frontend/src/features/knowledge/source-detail-page.tsx`: Studio mode nhận từ route, tái sử dụng Workspace cũ và API revision Kho tri thức hiện tại.
- `frontend/src/components/knowledge/ocr/ocr-inspector.tsx`: thêm nút Sửa/Textarea và callback hiệu đính; tái sử dụng Button; nội dung rỗng không tự hồi về Markdown cũ; toolbar wrap không cắt tabs. Năm ban hành lấy năm bốn chữ số trong ngày nhận diện, không tự gán năm hiện tại; chưa xác định thì ghi rõ.
- `backend/app/modules/knowledge/services/source_ingestion_service.py`: xử lý thứ tự đọc null trong manifest OCR. Ưu tiên order có giá trị (giữ 0), rồi reading_order, rồi vị trí khối; không sửa nội dung/layout, không OCR lại.
- `backend/tests/test_studio_nullable_reading_order.py`: 3 ca null/null, null/legacy, order=0. Trước sửa 2 failed/1 passed đúng TypeError; sau sửa đạt.

## Kiểm chứng

- 15 tests Studio/provenance trọng tâm đạt; Ruff toàn backend đạt (cảnh báo quyền thư mục cũ), Ruff scoped đạt.
- Frontend targeted Biome đạt; build bao gồm TypeScript đạt. Không quét toàn lint frontend theo fast-path AGENTS.
- Full backend: 826 passed, 13 failed, 2 skipped, 5 setup errors quyền thư mục pytest tạm. 13 failures cùng nhóm tồn tại #352 (RBAC/seed-facts/auth/reconciliation), không phải tuyên bố full suite đạt.
- Browser thật `col_admissions`, nguồn `bnd_0c0711c5539a`: mở từ nút Studio, ảnh/khung/Markdown 48 trang hiển thị, tab Thực thể hiện số 2705 và ngày ban hành, nút Sửa mở ô hiệu đính, F5 vẫn Studio. Không bấm Lưu/Duyệt hay thay đổi tài liệu user.
- Ảnh desktop: `storage/e2e_fixtures/353/studio-restored.jpg`; viewport mặc định hẹp xếp trên/dưới, desktop hai cột. Không kiểm chứng lại lưu/duyệt end-to-end hoặc OCR/embedding inference trong phiên này.

## Ranh giới và lưu ý

Không migration/reset DB, không sửa Kho tài liệu/qnu-sso/RAG/DAG/worker, không tạo vector hay xuất bản. Đây là phục hồi giao diện, không phục hồi API legacy và không coi nguồn đã OCR là đã vào Qdrant. Thực thể vẫn dùng logic suy luận sẵn có của UI cũ, không phải kết quả NER mới đã kiểm chứng. Luồng UI/ảnh dùng snapshot độc lập của Kho tri thức.

Bài học: khi phục hồi UI cần kiểm tra cả đường điều hướng và dữ liệu scan thật; unit fixture có số thứ tự đầy đủ sẽ bỏ sót null từ OCR thực tế. Tailscale server đã hoạt động khi user chạy dev ngoài sandbox; không khởi động worker từ sandbox trong phiên này.
