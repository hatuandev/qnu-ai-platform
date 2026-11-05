# Phiên 888 — Đánh giá RAG trong Cấu hình

## Phạm vi và thay đổi

Theo yêu cầu người dùng, bỏ nút Công cụ nâng cao cùng liên kết Quản trị chỉ mục/Đánh giá RAG khỏi trang kho. Đưa Đánh giá RAG vào **Cấu hình → Nhật ký & Bảo trì dữ liệu**, chỉ hiện với quản trị/editor sau khi xác định quyền. Trang chọn kho và trang đánh giá đánh dấu Cấu hình trên sidebar, không đánh dấu Kho tri thức. Giữ các route kỹ thuật cũ và cơ chế tự lập chỉ mục sau phát hành; không thay backend, dữ liệu hoặc dịch vụ.

- `frontendV1/src/features/knowledge/knowledge-detail-page.tsx`: bỏ CollectionAdvancedMenu/import thừa; giữ thao tác quản lý kho và toolbar hiện có.
- `frontendV1/src/features/settings/qnu-settings-hub.tsx`: liên kết dùng featureTarget hiện có. Có scope hợp lệ thì mở đúng kho; thiếu kho thì chọn lại. Không ghép collection của đơn vị khác vào scope hiện tại.
- `frontendV1/src/navigation/workspace-features.ts`: nhóm Cấu hình đơn vị và trạng thái sidebar cho evaluation.
- `frontendV1/tests/knowledge-actions-708.test.tsx`, `frontendV1/tests/settings-rag-entry-888.test.tsx`: regression vị trí công cụ, scope và quyền.
- Hướng dẫn35 cập nhật đường vào đánh giá.

## Kiểm chứng thực chạy

Cwd `frontendV1`:

- `npm exec -- vitest run tests/knowledge-actions-708.test.tsx tests/settings-rag-entry-888.test.tsx tests/navigation-scope-692.test.tsx tests/sidebar-navigation-691.test.tsx --reporter=dot`: **PASS**, exit0, 62/62 ca trong bốn file.
- `npm exec -- biome check --write src/features/knowledge/knowledge-detail-page.tsx src/features/settings/qnu-settings-hub.tsx src/navigation/workspace-features.ts tests/knowledge-actions-708.test.tsx tests/settings-rag-entry-888.test.tsx`: exit0, 0 lỗi; còn warning optional-chain cũ ở parentFolder. Chỉ sửa format/import trong phạm vi.
- `npm run build`: **PASS**, exit0, gồm TypeScript; cảnh báo bundle lớn vẫn còn.

Cwd root:

- Chromium chỉ đọc app đang chạy tại390px/1280px: toolbar không còn Công cụ nâng cao, Settings có Đánh giá RAG. Desktop chọn kho rồi mở đúng trang đánh giá, Cấu hình được đánh dấu; đã xem ảnh mobile Settings/desktop kho và evaluation. Không chạy benchmark, ghi dữ liệu, gọi model hoặc tạo index.
- Lần browser đầu **FAIL** assertion giữ kho khi chuyển sang Settings. Điều tra xác nhận root chuyển từ V1SessionGate sang AuthGate ở `/settings`, làm scope trong shell khởi tạo lại (hành vi có sẵn). Không đổi auth để đáp ứng thay đổi menu. Luồng thực tế an toàn mở màn chọn kho; kiểm chứng cuối kiểm đúng luồng này và mở đúng kho đã chọn. Đây là điều chỉnh giả định kiểm thử, không sửa assertion chất lượng retrieval hay thử lại inference.
- `git diff --check`: **PASS**.

Log/ảnh/script ở `tmp/check-888-*`, `tmp/fix-888-*`, không đưa vào Git. Backend/full suite/live RAG **NOT RUN**: không đổi contract hoặc hành vi retrieval. Không restart/reset/reindex/push; giữ thay đổi có trước trong checkout.

## Sử dụng

Tải lại giao diện. Vào Cấu hình → Nhật ký & Bảo trì dữ liệu → Đánh giá RAG, chọn kho rồi dùng bộ đánh giá hiện có. Trang kho chỉ còn các thao tác tài liệu/quản lý thường dùng. Việc lập chỉ mục tự động sau Duyệt & Phát hành được giữ nguyên.
