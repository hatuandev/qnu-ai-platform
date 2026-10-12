# Phiên #377 — Hiển thị rõ provider và bản chỉ mục vector

- Ngày: 2026-10-12.
- Mục tiêu: Tránh hiểu nhầm BGE-M3 chạy trên laptop; đồng bộ Nạp vector và tab Cấu hình.
- Skills frontend/admin-design/clean-code: tái sử dụng Select, trạng thái tải/lỗi trung thực, chỉnh FE có phạm vi và build cuối phiên; không chạy test Backend cho thay đổi FE.

## Thay đổi

- `frontend/src/features/knowledge/utils/vector-generation-label.ts`: nhãn chung model + provider (fallback ID thật) + chiều vector + Bản + trạng thái; địa chỉ chỉ hiển thị HTTP(S) origin, bỏ thông tin đăng nhập, query và path.
- `vector-load-controls.tsx`: tên provider cho các bản chỉ mục hiện hữu; máy chủ embedding theo lựa chọn; giải thích Bản là phiên bản chỉ mục, không phải nơi chạy model. Danh mục provider từ ModelOps, không hardcode server.
- `collection-models-tab.tsx`: phần chỉ mục đang phục vụ chatbot và máy chủ, tải lại chỉ mục định kỳ; tách khỏi mặc định cấu hình. Không dựa vào document_count legacy để kết luận kho trống; khóa thay model trực tiếp khi đã có generation và hướng dẫn tạo chỉ mục mới. Không báo đang dùng theo cấu hình chưa xuất bản.

## Kiểm chứng và giới hạn

- Biome mục tiêu: 3 file đạt, đã định dạng.
- `npm run build`: Vite và TypeScript đạt (exit 0).
- Không chạy Backend tests vì chỉ thay FE; chưa kiểm tra trực quan bằng browser/E2E.
- Kiểm tra DB read-only trước phiên: chỉ mục active `vg_8b7b06c28e51` dùng `prov_rtx5090_vllm`, model `bge-m3`, endpoint server AI cổng 8000; đây là cấu hình, không phải phép đo inference mới.
- Không reset, migration, nạp/xuất bản dữ liệu, đổi provider/key, khởi động lại worker hoặc đụng qnu-sso.

## Bài học

Tên model không xác định máy chạy inference; UI phải trình bày provider và phân biệt cấu hình mặc định với chỉ mục đã xuất bản.
