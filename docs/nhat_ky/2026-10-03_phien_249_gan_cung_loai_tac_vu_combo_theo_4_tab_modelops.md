# Nhật Ký Phiên Làm Việc #249 — Gán Cứng Loại Tác Vụ Combo Theo 4 Tab ModelOps & Khóa Chặt Ngữ Cảnh

- **Thời gian**: 2026-10-03 23:30 (Giờ Việt Nam)
- **Tác giả**: AI Pair Programmer & Senior Full-Stack Architect
- **Chủ đề**: Tái cấu trúc UX/UI Quản lý Chuỗi Combo Dự Phòng (ModelOps Failover Combos) theo 4 Tab chuyên trách độc lập: **Vision & OCR**, **Vector Embedding**, **Xếp Hạng Reranker**, và **LLM Chat**.

---

## 1. Vấn Đề Nghiệp Vụ & Phản Hồi Từ Người Dùng

- **Hiện trạng gây nhầm lẫn**:
  - Giao diện ModelOps bên ngoài đã phân định rõ ràng thành 4 Tab (`Vision & OCR`, `Vector`, `Xếp Hạng`, `Chat LLM`).
  - Tuy nhiên, bên trong Modal "Tạo / Chỉnh Sửa Combo" lại hiển thị 4 nút bấm chuyển đổi `[Vision OCR] [Embedding] [Reranker] [LLM Chat]`.
  - Khi người dùng bấm qua lại giữa các nút, danh sách mô hình bên dưới không đổi, khiến người dùng lầm tưởng: *"1 Combo có thể kiêm nhiệm cả 4 chức năng"* hoặc *"Đây là các tab để cấu hình 4 chức năng trong cùng 1 combo"*.
  - Dòng checkbox mặc định ở đáy thay đổi nhãn theo nút bấm (`...cho kênh tác vụ OCR` vs `...cho kênh tác vụ CHAT`) gây hoang mang và tiềm ẩn rủi ro lưu nhầm kênh tác vụ.

---

## 2. Giải Pháp Kỹ Thuật Triệt Để (Gán Cứng & Khóa Chặt Ngữ Cảnh)

1. **Xóa Bỏ 100% 4 Nút Hoán Đổi Trong Modal**:
   - Thay thế toàn bộ cụm 4 nút bấm bằng **Thẻ Thông Tin Gán Cứng (Locked Banner)**:
     - Kênh tác vụ được hiển thị cố định kèm Icon, màu sắc nhận diện và Badge `[Gán Cứng Cố Định]`.
     - Có mô tả nghiệp vụ chi tiết cho từng kênh (Vision OCR chỉ bóc tách scan/ảnh, Embedding chỉ nhúng vector, Reranker chỉ tái xếp hạng, Chat chỉ đàm thoại LLM).
     - Người dùng không thể và không cần bấm chuyển đổi loại tác vụ trong Modal nữa.
2. **Kế Thừa Tác Vụ Tự Động Từ Tab Đang Đứng (Tab-Aware Creation)**:
   - Nút `+ Tạo Combo` ở Header tự động nhận diện Tab người dùng đang chọn:
     - Đứng ở Tab `Vision & OCR` ➔ Nút hiển thị: `Tạo Combo (OCR)` ➔ Mở modal gán cứng `ocr`.
     - Đứng ở Tab `Vector` ➔ Nút hiển thị: `Tạo Combo (Vector)` ➔ Mở modal gán cứng `embedding`.
     - Đứng ở Tab `Xếp Hạng` ➔ Nút hiển thị: `Tạo Combo (Reranker)` ➔ Mở modal gán cứng `reranker`.
     - Đứng ở Tab `Chat LLM` ➔ Nút hiển thị: `Tạo Combo (Chat)` ➔ Mở modal gán cứng `chat`.
3. **Tự Động Chuẩn Hóa Khi Chỉnh Sửa (Auto-Resolve on Edit)**:
   - Hàm `handleOpenEditModal` tự động nhận diện và bảo vệ kênh tác vụ của combo dựa trên tên và tab đang đứng (ví dụ `qnu-ocr-master` luôn luôn được mở với `task_type = "ocr"`).
4. **Cảnh Báo Mô Hình Không Hợp Lệ & Lọc Nghiêm Ngặt**:
   - Tự động đóng khung đỏ và gắn cờ `[Không có Vision OCR]` đối với các mô hình text thuần túy (như `qwen/qwen3.8-27b`) nằm trong chuỗi OCR.
   - Bộ chọn thêm mô hình (`candidateModelsForTask`) chỉ hiển thị đúng các model tương thích với kênh tác vụ được gán cứng.

---

## 3. Các Tệp Mã Nguồn Thay Đổi

- [frontend2/src/components/modelops/combos-vision-section.tsx](file:///d:/DuAnPhanMem/qnu-ai-platform/frontend2/src/components/modelops/combos-vision-section.tsx):
  - Thay thế cụm button chọn Task Type bằng thẻ thông tin gán cứng.
  - Cập nhật nút Header `+ Tạo Combo` mang nhãn động và truyền đúng `task_type` theo Tab.
  - Thêm logic tự động chuẩn hóa tác vụ trong `handleOpenEditModal`.
  - Cảnh báo mô hình không có thị giác đọc ảnh trong danh sách bước thực hiện.
- [AGENTS.md](file:///d:/DuAnPhanMem/qnu-ai-platform/AGENTS.md):
  - Bổ sung chính thức Tôn chỉ số 10 về việc tự động đồng bộ Memory và Nhật ký sau mỗi phiên Vibe Coding.

---

## 4. Kết Quả Nghiệm Thu

- Giao diện đạt độ trong sáng (clarity) tối đa: mỗi Tab quản lý đúng loại combo của mình, mỗi combo chỉ chuyên trách đúng 1 kênh tác vụ duy nhất.
- Hoàn toàn chấm dứt tình trạng nhầm lẫn giữa OCR và Chat trên UI ModelOps.
