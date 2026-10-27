# Context624 — Thử lại đúng bước 8 qua 9router

Ngày 24/10/2026. Người dùng xác nhận 9router đang hoạt động và yêu cầu thử lại bước 8. Phạm vi này cho phép một lượt retry riêng; không chạy lại các bước 1–7 hoặc toàn compiler.

**Kết quả: PASS, exit 0.**

| Mục | Quan sát thực tế |
|---|---|
| Model | `gh/gpt-5.6-luna`; phản hồi ghi `gpt-5.6-luna` |
| Thời gian gọi và kiểm tra phản hồi | 10,734 giây |
| Timeout giữ nguyên | 30 giây |
| Số lần gọi retry | 1; không format correction hoặc fallback |
| Kết thúc | `finish_reason=stop` |
| Phân loại | 52 proof liên quan + 12 không liên quan; đủ 64/64, không trùng, không ngoài offer |
| Token quan sát | 18.713 input / 1.247 output |
| Nội dung gửi | Hash schema/instruction/payload khớp request8 đã lưu |
| Cấu hình | Configuration hash khớp lượt gốc |
| Lưu/đọc output | Qua LocalStorageDriver, JSON khớp hoàn toàn |

Môi trường được kiểm lại trước gọi: DB test local có nonce sở hữu đúng, MinIO/Qdrant cấu hình local, ba nguồn và snapshot381proof giữ nguyên. Credential lấy qua ModelOps được bảo vệ; không dùng CLI/API-key fallback, không đổi model mặc định hoặc timeout.

Đã lưu receipt riêng ở `backend/storage/context624/stage8/`. Request/output qua Storage tạm tại prefix `context624-stage8-retry/`. Các file chứa nguồn tiếp tục nằm trong Storage riêng, không sao chép vào Git.

Seals xác nhận job/checkpoint cũ, request8 cũ, bảy output trước, toàn bộ file app và các hàng source/default/provider/index không đổi. Dấu vết ReadTimeout cũ vẫn còn `uncertain`; lần retry mới không được dùng để giả mạo kết quả upstream của lần cũ.

Đây là PASS của bước8: model đã trả về phân loại nguồn hợp lệ. **Chưa chạy bước9 trở đi và chưa nghiệm thu toàn compiler.** Kết quả retry chưa được gắn vào job cũ; cơ chế resume hiện có vẫn không nhận checkpoint uncertain. Nếu tiếp tục, cần quy trình phục hồi có audit phù hợp với xác nhận của người dùng, không sửa tay status hoặc xóa stage để vượt guard.

Không sửa mã ứng dụng, không full Pytest hoặc benchmark64 vì không đổi code. Kết quả full3785PASS/18FAILnền/17SKIP thuộc Context623, không phải test mới. Không reindex, publish, restart, commit hoặc push. DB/Storage acceptance tiếp tục giữ theo lựa chọn trước của người dùng.
