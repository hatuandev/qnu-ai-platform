# Phiên 735 — Sửa E2E tự động lưu capacity

Ngày: 2026-10-30. Người dùng báo `capacity_status` vẫn chặn navigation sau khi provider và các probe đã đạt.

## Căn cứ và nguyên nhân

- Phiên live `7f9361961005`: discovery trả đủ metadata của bốn model nhưng cả bốn bản ghi vẫn unknown, token limits rỗng; không có sự kiện sync capacity.
- API đang chạy đã có route sync. Lỗi nằm ở bootstrap E2E: provider-setup đăng ký model nhưng chưa áp dụng snapshot discovery, nên probe đạt không chứng minh capacity đã được lưu.
- Qwen công bố context 131072/output 16384; Nemotron 16384/8192; BGE context 8192, embedding dimension 1024. Không dùng giá trị đoán để thay metadata thiếu.

## Thay đổi

- `frontendV1/e2e/stages/providers.spec.ts`: gửi discovery_check_id khi đăng ký và gọi helper sync sau khi đủ bốn model.
- `frontendV1/e2e/stages/provider-capacity.ts`: đồng bộ qua API từ snapshot hiện hành, kiểm đúng parent, endpoint, model, capability, active và capacity configured; lỗi/conflict không có fallback giả.
- `scripts/e2e_profiles/qnu-server.json`: khai báo riêng thông số vận hành E2E đã có căn cứ: chat timeout 300s; OCR 180s; embedding/rerank 60s; rerank input 1024. Chỉ bổ sung input/OCR còn thiếu, giữ cấu hình operator đã có.
- OCR bound 4096 cho ảnh tối đa 1664 × 2048 và prompt đã ghim theo [bằng chứng phiên 728](2026-10-30_phien_728_luu_capacity_va_test_model_live.md). Đây là profile thử của server/processor tương ứng, không phải capacity mặc định của mọi Nemotron.
- Thêm tám regression trong `frontendV1/tests/e2e-capacity-735.test.ts`, gồm snapshot, metadata thiếu, conflict, sai parent, giữ operator config và kiểm hash prompt OCR.
- Cập nhật hướng dẫn ngắn, đầy đủ, hướng dẫn model và README E2E: provider-setup tự sync; UI kiểm lại là tùy chọn. Phiên cũ chưa upload có thể chạy lại setup rồi probe/navigation.
- Giữ Qwen 128K/16K và Compiler output 8192. Không sửa backend trong phiên này, không restart/cleanup/init hay xóa nguồn.

## Kiểm chứng thực chạy

| Kiểm tra | Kết quả |
| --- | --- |
| Vitest: e2e-capacity-735, capacity-discovery-733, e2e-request-timeout-730 | PASS: 15 test, 3 file |
| `npm run build` | PASS |
| `npm run test:e2e:typecheck` | PASS |
| Biome ba file TypeScript sửa/thêm | PASS, không cảnh báo |
| `python -m pytest scripts/test_e2e_provider_setup.py -q` | PASS: 4 test |
| Live provider-setup, model-discovery, model-chat, model-embedding, model-rerank, model-ocr, navigation | PASS: 7 chặng trên cùng phiên |

Log kiểm chứng tại `tmp/capacity-735-unit.log`, `tmp/capacity-735-build.log`, `tmp/capacity-735-provider.log`, `tmp/capacity-735-live.log`. Báo cáo stage dưới `tmp/v1-e2e/7f9361961005/runs/`.

API sau sửa xác nhận cả bốn model configured, metadata context/output/dimension đúng server; profile timeout/input/OCR được lưu. Không có nguồn hoặc bản phát hành trước thao tác, chỉ thay cấu hình trong môi trường E2E và tạo workspace thử qua navigation.

## Giới hạn và bước tiếp

- Upload trở đi NOT RUN trong phiên này; chưa nghiệm thu toàn luồng, không thay đổi gate review hoặc ba finding hình ảnh cũ.
- Full backend không chạy lại: không đổi backend. Kết quả full suite Windows access violation phiên 733 vẫn là FAIL lịch sử, không đổi thành PASS.
- Nhánh tạo model mới được regression kiểm; live lần này áp dụng cho bốn model đã đăng ký.
- Người dùng giữ serve và chạy ` .\test-v1-e2e.ps1 run upload --headed` từ phiên hiện tại. Không cần cleanup/init.

[Hướng dẫn chạy lại](../quy_trinh/V1_QUY_TRINH_TEST_LAI.md).
