# Nhật ký phiên 903 — Pilot và đóng phạm vi bản đầu

- Ngày: 2026-11-08.
- Nhánh: `feat/v1-user-workflow`, baseline `09a173a2`.
- Kế hoạch nguồn: [15 — Trải nghiệm người dùng QNU V1](../ke_hoach/15_ke_hoach_trai_nghiem_nguoi_dung_qnu_v1.md), gói P7.
- Trạng thái: bộ công cụ pilot và gate tự động đã hoàn tất; **phiên pilot thực tế NOT RUN** vì chưa chọn đơn vị/người tham gia và DB ứng dụng chưa áp migration `0015`–`0017`. Không commit/push, không deploy/migrate DB ứng dụng.

## 1. Yêu cầu và giả định

Yêu cầu của người dùng: “tiếp tục giai đoạn 7” — pilot và đóng phạm vi bản đầu.

Giả định đã dùng, bám theo P7 trong kế hoạch 15:

- P7.1 và P7.2 cần người thật trong một đơn vị thật và môi trường đã migrate; agent không thể chọn người, thao tác hộ hoặc tự tuyên bố kết quả pilot.
- Phần có thể bàn giao trước phiên pilot: tiêu chí chọn người, kịch bản tác vụ có đo thời gian, ma trận tình huống lỗi/thiếu quyền/thiếu cấu hình/xung đột nguồn/sync chưa xong, quy tắc phân loại S1–S4, checklist nghiệm thu, known limitations và runbook rollout/rollback.
- Bất biến cứng của P7 (“không vượt quyền, không phục vụ draft/withdrawn, không báo ready sai”) phải kiểm được bằng test tự động trên DB cô lập trước khi cho người dùng vào pilot.
- Không tự triển khai production chỉ vì test đạt; kết quả gate không thay thế biên bản pilot.

## 2. Thay đổi

Không sửa mã backend/frontend trong P7. Tài liệu mới/cập nhật:

- Mới [46 — Pilot QNU V1 và đóng phạm vi bản đầu](../quy_trinh/46_pilot_qnu_v1_va_dong_pham_vi.md):
  - §1 điều kiện vào pilot (migration `0015`–`0017`, backup, workspace/corpus/provider được phép, vai trò điều phối/ghi biên bản/verifier).
  - §2 P7.1 tiêu chí chọn đơn vị, bảng 3–5 người đề xuất theo editor/reviewer/admin/người tra cứu và mẫu ghi ẩn danh.
  - §3 P7.2 kịch bản T1–T6 (thêm tài liệu, gửi duyệt/yêu cầu sửa, duyệt, xuất bản/đồng bộ, hỏi đáp có dẫn chứng, cập nhật bản mới) kèm bảng đo thời gian thao tác, thời gian chờ và số lần dev hỗ trợ.
  - §4 P7.3 ma trận 12 tình huống không chỉ golden path, hành vi trung thực mong đợi và dấu hiệu FAIL cứng.
  - §5 P7.4 phân loại S1–S4 và giới hạn sửa trong phạm vi UX, không refactor toàn repo.
  - §6 P7.5 checklist nghiệm thu, known limitations và rollout/rollback tham chiếu tài liệu triển khai.
  - §7 lệnh gate tự động, bản đồ bất biến → test và receipt lần chạy.
  - §8 mẫu biên bản pilot ẩn danh.
- Cập nhật [quy_trinh/README.md](../quy_trinh/README.md): thêm mục 46 vào nhóm luồng hệ thống V1.
- Cập nhật [kế hoạch 15](../ke_hoach/15_ke_hoach_trai_nghiem_nguoi_dung_qnu_v1.md): P7 có bộ công cụ + gate, pilot thực tế NOT RUN.

## 3. Phương pháp và lệnh thật

Từ `backendV1`, harness DB cô lập (không dùng DB ứng dụng):

```bash
export DATABASE_URL="$(grep -m1 '^DATABASE_URL=' ../.env | cut -d= -f2-)"
uv run python scripts/run_isolated_tests.py \
  tests/integration/test_workspaces_modelops_api.py \
  tests/integration/test_workspace_model_boundaries.py \
  tests/integration/test_index_readiness_819.py \
  tests/integration/test_publication_index_sync_878.py \
  tests/integration/test_assistant_readiness_p6.py \
  tests/integration/test_answer_review_p6.py -q
```

Kết quả: `43 passed, 2 warnings` trong 167,88s; receipt `qnu_v1_test_002421364e204f88`, `db_dropped: true`, `legacy_sentinel_preserved: true`, `pytest_exit: 0`, `seconds: 176.42`.

Phạm vi gate đã chạy:

- Tách quyền workspace, không leo thang qua body/header, thu hồi membership có hiệu lực ngay.
- Readiness chỉ `ready` khi binding khớp; collection rỗng/chưa index không báo ready.
- Publish/withdraw/sync: không kích hoạt nội dung stale, giữ dẫn chứng, retry idempotent.
- Answer review chỉ chạy trên nguồn đã xuất bản, giữ `insufficient_evidence` trung thực, nhãn do người kiểm tra.

Không chạy lại Ruff/frontend vì P7 không sửa mã. Các kết quả P6 vẫn là mốc gần nhất cho frontend.

## 4. NOT RUN

- **Phiên pilot thật (P7.1–P7.3): NOT RUN** — chưa chọn đơn vị/người tham gia; chưa có biên bản thời gian, lỗi hay số lần dev hỗ trợ. Không có số liệu để kết luận mục tiêu ≥80%.
- **Nghiệm thu P7.5: NOT RUN** — checklist người dùng, phân biệt trạng thái chuẩn bị/chờ duyệt/đang đồng bộ/sẵn sàng và so sánh chất lượng/latency cùng corpus/model/snapshot chưa có biên bản.
- **Kiểm trình duyệt desktop/mobile: NOT RUN** — API/web không chạy; DB ứng dụng còn ở `0014_publication_index_sync`, migration `0015`–`0017` chưa áp dụng và migrate DB ứng dụng nằm ngoài phạm vi được giao.
- Không deploy, không migrate DB ứng dụng, không reindex, không gọi model thật, không restart dịch vụ.

## 5. Rủi ro và bước sau

- Áp migration `0015`–`0017` trên môi trường staging được phép, sau backup và kiểm `alembic current`; chạy lại gate §7 trước khi mời người dùng.
- Chọn đơn vị và 3–5 người theo §2; chạy T1–T6 và ma trận §4; ghi biên bản ẩn danh theo §8.
- Xử lý S1 ngay (dừng pilot), S2 trong phạm vi UX kèm regression; S3 gom đợt nhỏ; S4 đưa vào backlog E1–E6.
- Full backend suite vẫn **NOT COMPLETED** trong các phiên P4–P6; lỗi nền Redis751 cần xử lý riêng. Không tuyên bố toàn hệ thống PASS.
- Chốt nghiệm thu/known limitations/rollout sau khi có biên bản; không tự triển khai production. Chưa commit/push khi chưa có xác nhận.
