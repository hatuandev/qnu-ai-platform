# QNU.AI Platform — Frontend Studio UI

Giao diện Quản trị và Điều phối Trợ lý AI Thông minh Trường Đại học Quy Nhơn, xây dựng trên kiến trúc **Single Page Application (SPA)** siêu nhẹ với **Vite 6/8 + React 19 + TypeScript + Tailwind CSS v4 + Biome + TanStack Suite**.

---

## 🚀 Tính Năng & Điểm Nhấn Kiến Trúc

1. **Hiệu Năng Vượt Trội**:
   - Khởi động cực nhanh, Hot Module Replacement (HMR) dưới 50ms.
   - Serve tĩnh qua Nginx chỉ tiêu tốn ~15–20MB RAM trên máy chủ Dokploy (thay vì 200MB+ của Next.js SSR).
   - Biome linter/formatter kiểm tra mã nguồn siêu tốc (< 15ms).
2. **Đồng Bộ Hệ Thống Thiết Kế QNU (QLKTX)**:
   - Hệ màu **OKLCH** với sắc xanh Teal học thuật đặc trưng: `--primary: oklch(0.46 0.13 160)`.
   - Hỗ trợ Dark/Light mode tự động, chuẩn hóa bán kính bo góc 6px control, 8px surface.
3. **AI Suite Components**:
   - Trực quan hóa đồ thị quy trình 05 Trợ lý AI qua `@xyflow/react` (Visual DAG Canvas).
   - Bắt luồng Server-Sent Events (SSE Token Streaming) mượt mà với `eventsource-parser`.
   - Ngăn kéo tra cứu dẫn chứng văn bản gốc (`CitationSheet`) phục vụ kiểm định chống ảo giác (Anti-Hallucination).

---

## 🛠️ Lệnh Phát Triển & Kiểm Tra

```powershell
# 1. Cài đặt thư viện phụ thuộc
npm install

# 2. Khởi chạy máy chủ phát triển (cổng 3001, tự động reverse proxy API 8001)
npm run dev

# 3. Kiểm tra định dạng và lỗi cú pháp (Biome)
npm run lint
npm run format

# 4. Kiểm tra kiểu dữ liệu TypeScript
npm run typecheck

# 5. Đóng gói bản phát hành Production
npm run build
```

Địa chỉ truy cập ứng dụng: `http://localhost:3001`
Tài liệu REST API Backend: `http://localhost:8001/docs`
