# Phiên717 — Tinh gọn frontendV1 và hoàn thiện luồng demo tải tài liệu đến hỏi đáp có trích dẫn

## Yêu cầu và phạm vi

- Tổ chức lại điều hướng `frontendV1` thành 6 mục Sidebar chính (`Tổng quan`, `Kho tri thức`, `Trợ lý AI`, `Hội thoại`, `Tác vụ`, `Cấu hình`); đặt bộ chọn Đơn vị (`WorkspaceSwitcher`) cố định trên thanh đầu trang (`Topbar`), bỏ lặp bộ chọn Đơn vị ở Sidebar và thân trang `Tổng quan`.
- Đưa các chức năng về đúng ngữ cảnh: OCR/chính tả trong chi tiết tài liệu; Biên soạn và Phát hành trực tiếp bên trong kho; Tìm kiếm thử, Hỏi đáp trên kho và Đánh giá RAG thành menu `Công cụ nâng cao` trong kho; gom các trang quản trị/vận hành vào trung tâm `Cấu hình` (`/settings`) có phân biệt cấu hình Đơn vị và Toàn nền tảng.
- Nối tải lên tài liệu và phiên bản mới gửi `auto_extract="true"`, dùng trực tiếp `source.processing` trả về từ BE, không gọi thêm API tạo OCR run trùng lặp.
- Bổ sung phần trăm và hiệu ứng xử lý thật (`ProcessingProgress`) dùng chung cho danh sách tài liệu, chi tiết tài liệu, hộp thoại tải lên và trang Tác vụ; cập nhật counter trang bền vững ở BE (`pages_done`, `pages_failed`) trong quá trình chạy và thêm liên kết nguồn/bản biên soạn cho `JobView`.
- Hoàn thiện luồng Trợ lý AI (`Chat thử`, trạng thái sẵn sàng chức năng Hội thoại), `CitationSheet` (mở về tài liệu nguồn/revision/trang và bản phát hành) và trang `Tác vụ` (mặc định là danh sách công việc, tách Sao lưu/Dọn dữ liệu sang `Cấu hình`).
- Giữ nguyên thay đổi chưa commit của người dùng (đặc biệt là Context716 xóa vĩnh viễn tài liệu nguồn). Không chạy Pytest/Vitest/E2E, không gọi model hoặc chạy luồng với tài liệu thật.

## Thay đổi

- **Điều hướng 6 mục & Topbar/Cấu hình Hub:**
  - `navigation/workspace-features.ts`, `navigation/config.ts`, `navigation/use-feature-scope.tsx`, `navigation/utils.ts`: cấu hình 6 mục chính dùng chung cho Sidebar, Command Menu (`Ctrl+K`), Breadcrumb và trạng thái active (bao gồm active `Cấu hình` cho các route con thuộc Đơn vị và Toàn nền tảng); giữ nguyên URL ngắn, liên kết trích dẫn và đường dẫn cũ.
  - `layouts/topbar.tsx`, `layouts/workspace-switcher.tsx`, `layouts/workspace-sidebar.tsx`, `layouts/app-sidebar.tsx`, `layouts/qnu-command-menu.tsx`: chuyển `WorkspaceSwitcher` lên `Topbar` (chế độ compact), tinh gọn Sidebar còn 6 mục chính.
  - `features/settings/qnu-settings-hub.tsx`, `routes/settings.index.tsx`, `features/settings/settings-layout.tsx`, `features/workspaces/qnu-dashboard-page.tsx`: xây dựng trang trung tâm `Cấu hình` gồm 4 nhóm (`Kết nối AI`, `API tích hợp`, `Đơn vị & Phân quyền`, `Nhật ký & Bảo trì dữ liệu`), bỏ lặp thẻ chọn đơn vị trên trang `Tổng quan`.
- **Tiến độ xử lý thật & Tự động bóc tách:**
  - `backendV1/qnu/domains/ocr/execution.py`, `backendV1/qnu/domains/ocr/automatic.py`: bổ sung `_refresh_page_counters` cập nhật `run.pages_done` và `run.pages_failed` trước các checkpoint `commit_owned` để API trả tiến độ trang thực tế khi đang xử lý.
  - `backendV1/qnu/domains/operations/schemas.py`, `backendV1/qnu/domains/operations/jobs/catalog.py`: thêm `source_id`, `revision_id`, `compilation_run_id` vào `JobView`.
  - `features/knowledge/processing-progress.tsx`, `requests.ts`, `queries.ts`, `ocr-types.ts`, `source-upload-dialog.tsx`, `revision-upload-dialog.tsx`: gửi `auto_extract="true"` khi tải lên, hiển thị tiến độ thật theo trang/giai đoạn kèm `aria-busy` và `motion-reduce`, polling TanStack Query 3–4 giây khi active và dừng khi hoàn tất/lỗi.
- **Kho tri thức, Trợ lý AI, Hội thoại & Tác vụ:**
  - `features/knowledge/knowledge-detail-page.tsx`, `source-detail-page.tsx`, `compilation-detail-page.tsx`, `compiled-document-detail-page.tsx`, `compiled-version-detail-page.tsx`: mở trực tiếp `Tài liệu` · `Biên soạn` · `Phát hành` và menu `Công cụ nâng cao` ngay trong kho (bỏ các màn trung gian); gom Download/Bóc tách lại/Phiên bản mới/Vòng đời vào menu `⋯`; hiển thị rõ điều kiện chuyển bước và phân biệt `"Đã phát hành"` với `"Sẵn sàng hỏi đáp"` kèm nút `"Cập nhật tìm kiếm"`.
  - `features/assistants/assistants-panel.tsx`, `assistant-detail-page.tsx`, `features/conversations/citation-sheet.tsx`, `chat-view.tsx`: thêm nút `"Chat thử"`, cập nhật trạng thái sẵn sàng chức năng Hội thoại, bổ sung liên kết từ trích dẫn về đúng tài liệu nguồn (kèm revision/trang) và bản phát hành.
  - `features/operations/types.ts`, `queries.ts`, `operations-page.tsx`, `job-details.tsx`: mặc định hiển thị danh sách công việc với `ProcessingProgress` và liên kết về tài liệu/bản biên soạn; tách Sao lưu, Dọn dữ liệu và `ReadinessPanel` sang các chế độ xem của `Cấu hình`.

## Kiểm tra thực chạy

- Scoped Ruff check & Ruff format (`backendV1` — 4 file): PASS (`All checks passed!`, `4 files already formatted`).
- Scoped Biome check (`frontendV1` — 32 file): PASS (`0 errors`, `0 warnings`).
- TypeScript `npm run typecheck` (`tsc --noEmit`): PASS (exit 0).
- Production bundle `npm run build` (`vite build && tsc --noEmit`): PASS (exit 0, built in 6.37s).
- Pytest, Vitest, Playwright/E2E và live model/tài liệu thật: **NOT RUN** theo đúng giới hạn phiên.

## Giới hạn và bước tiếp theo

- Phiên này không chạy test tự động (Pytest/Vitest/E2E), không gọi model thật, không migrate DB và không tự khởi động lại `v1-dev`.
- Khi cần nghiệm thu runtime trên trình duyệt, khởi động lại `v1-dev` để worker/API nạp thay đổi counter tiến độ và `JobView`, sau đó kiểm tra luồng tải tệp PDF/DOCX → tự bóc tách → biên soạn → phát hành → cập nhật chỉ mục → tạo trợ lý → hỏi đáp và mở trích dẫn.

