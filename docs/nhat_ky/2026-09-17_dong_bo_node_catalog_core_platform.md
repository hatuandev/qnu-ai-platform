# Nhật Ký Công Việc — Đồng bộ Node Catalog từ qnu-ai-core sang qnu-ai-platform

- **Ngày**: 2026-09-17
- **Mục tiêu**: Điều tra vì sao `/nodes` trên Platform không hiển thị danh mục Node giống `qnu-ai-core` và triển khai lại đúng contract.

## Phân tích nguyên nhân

- Core dùng `services/studio-ui/app/nodes/page.tsx` làm trang Node Catalog, gọi `GET /nodes` và đọc `NodeCatalogResponse.items`.
- Platform trước đó ánh xạ `/nodes` vào DAG Canvas; backend chưa có endpoint `/platform/v1alpha1/nodes`, nên UI không thể nhận danh mục manifest.
- DAG Canvas được giữ ở đường dẫn `/canvas` để phân biệt rõ catalog Node và trình thiết kế workflow.

## Thay đổi kỹ thuật

| Tệp | Hành động | Mô tả |
|---|---|---|
| `configs/nodes/*.v1alpha1.json` | Thêm mới | Sao chép 13 NodeManifest chuẩn từ `qnu-ai-core/packages/contracts/examples/nodes`. |
| `backend/app/modules/node_catalog/` | Thêm mới | Module loader bất đồng bộ, DTO và router Core-compatible; đọc file UTF-8, NFC, lọc theo search/category/status. |
| `backend/app/main.py` | Cập nhật | Mount `/platform/v1alpha1/nodes`. |
| `frontend/src/services/api-client.ts` | Cập nhật | Thêm typed client `getNodeCatalog()` và kiểm tra runtime payload. |
| `frontend/src/pages/node-catalog-page.tsx` | Thêm mới | Trang catalog lấy dữ liệu thật, filter/search, trạng thái loading/error/empty. |
| `frontend/src/components/admin/node-catalog-card.tsx` | Thêm mới | Card Node hiển thị metadata và số lượng schema properties. |
| `frontend/src/components/admin/node-manifest-dialog.tsx` | Thêm mới | Xem schema Input/Output/Config và sao chép manifest JSON. |
| `frontend/src/App.tsx` | Cập nhật | `/nodes` mở catalog; `/canvas` mở DAG Canvas; sửa các liên kết điều hướng. |
| `backend/tests/test_node_catalog.py` | Thêm mới | Kiểm thử API, filter và trạng thái catalog directory không tồn tại. |

## Kết quả kiểm thử

- `uv run ruff check .`: đạt, 0 lỗi.
- `uv run pytest -q`: **139/139 passed**.
- `npm.cmd run lint`: đạt, Biome 0 lỗi.
- `npm.cmd run typecheck`: đạt, TypeScript 0 lỗi.
- `npm.cmd run build`: thành công.
- Kiểm tra trực tiếp: trang `http://localhost:3001/nodes` đã render catalog mới; backend đang chạy là tiến trình cũ nên trả 404 cho endpoint mới. Cần restart backend port 8001 để nạp code mới.

## Lưu ý session song song

- Không chỉnh sửa các file Provider/ModelOps đang được session khác xử lý.
- Không dừng tiến trình backend hiện tại để tránh ảnh hưởng session khác; việc restart được để lại như bước vận hành sau khi người dùng xác nhận thời điểm phù hợp.
