# Phiên734 — Cập nhật hướng dẫn test lại từ đầu

Người dùng yêu cầu sửa hướng dẫn để tự chạy từ đầu sau thay đổi capacity733.
Đọc context/diff, đối chiếu script init/serve, profile model và lệnh thực tế.
Chỉ sửa tài liệu; giữ diff ứng dụng733, không chạy cleanup/init/test/inference,
không restart hay đổi DB phục vụ.

- Bản ngắn V1_QUY_TRINH_TEST_LAI: chỉ rõ mục B cho phiên mới, hai cửa sổ,
  dừng serve/đóng tab cũ trước cleanup, provider-setup một lần rồi tạm dừng lệnh.
- Tích hợp bước Nhập từ /models → Lấy lại → chọn4model đã có → Áp dụng trước probe;
  bảng thông số server mới, không bắt nhập tay context/output/dimension nữa.
- Tách timeout vận hành khỏi capacity; Qwen300s/BGE60s/OCR180s, Compiler8192 giữ.
  OCR bound4096/1664×2048/hash prompt vẫn cần bổ sung theo căn cứ đã đo khi cùng
  server/processor/prompt. Input riêng reranker1024 chỉ là chính sách thử cũ.
- Giữ đủ14chặng theo đúng thứ tự, PASS mới đi tiếp; status/report khi lỗi,
  needs_attention/uncertain không bỏ qua. Mục hình OCR ghi rõ là lượt trước.
- Đồng bộ bản đầy đủ V1_TEST_TOAN_LUONG_MODEL_QNU và frontendV1/e2e/README,
  sửa số mục kết thúc từ7thành6; hướng dẫn resume vẫn giữ.

Kiểm tĩnh: hai hướng dẫn có đủ14stage đúng thứ tự; PowerShell Parser kiểm18khối
lệnh không thực thi, exit0. Kiểm link mới/UTF-8 không BOM/LF/diff. Không chạy test
ứng dụng cho tài liệu. Kết quả733 là lịch sử:73BE trọng tâm/22FE đạt, full backend
chưa hoàn tất do Windows access violation, chưa nghiệm thu full E2E mới.

[Hướng dẫn ngắn](../quy_trinh/V1_QUY_TRINH_TEST_LAI.md).
[Hướng dẫn đầy đủ](../quy_trinh/V1_TEST_TOAN_LUONG_MODEL_QNU.md).
[Snapshot734](../memory/snapshots/2026-10-30_session_734.md).
