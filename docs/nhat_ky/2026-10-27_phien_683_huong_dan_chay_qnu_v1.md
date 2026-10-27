# Phiên 683 — Hướng dẫn chạy QNU V1

## Yêu cầu và phạm vi

Người dùng yêu cầu viết file hướng dẫn chạy phiên bản V1. Chỉ bổ sung tài liệu,
không sửa ứng dụng, cấu hình phục vụ hoặc thực hiện thao tác vận hành.

Đọc AGENTS, PROJECT_CONTEXT, workflow/memory, security/Git và bảng kiểm chứng.
Không có AGENTS riêng trong `docs/`. Git hiện có nhiều thay đổi của người dùng;
`backendV1/` và `frontendV1/` còn untracked, nên đối chiếu file thật và hash thay
vì coi diff rỗng là không đổi.

## Kết quả

Thêm [hướng dẫn chạy V1](../quy_trinh/38_huong_dan_chay_qnu_v1.md):

- Ba cửa sổ API, ARQ worker, FE; cổng 8002/3001 và các URL kiểm tra.
- Hai cách giữ đúng thư mục chạy theo `.env` gốc hoặc `backendV1/.env`;
  cảnh báo đường dẫn storage tương đối và môi trường của API/worker phải khớp.
- Cài dependency từ lockfile, hạ tầng Docker tùy chọn, migration và head thật
  `0003_rag_policy_metadata`; không dùng CLI placeholder hoặc runner legacy.
- Admin dev tự đăng nhập qua cầu nối hiện có, ModelOps credential/capacity,
  allowlist/default/quota theo workspace; không sao chép secret vào tài liệu.
- Luồng upload → OCR → sửa → Compiler/review → con người duyệt/xuất bản → index
  → hỏi đáp, xử lý lỗi và dừng/chạy lại.

Không áp dụng skill sửa BE/FE vì không sửa mã hoặc hợp đồng ứng dụng. Cập nhật
mục lục quy trình, nhật ký, WORK_LOG, PROJECT_CONTEXT và snapshot683, giữ lịch sử.

## Kiểm chứng thực chạy

Cwd gốc repo, PowerShell và Python sẵn có của `backendV1/.venv`:

- Đọc mã/config/README, migration, `uv help run`, kiểm tra Git/diff liên quan.
- Parser PowerShell phân tích **14 khối lệnh**, không có lỗi cú pháp, exit0.
  Chỉ parse, không thực thi các lệnh khởi động/cài đặt trong hướng dẫn.
- `python storage/artifacts/context683-huong-dan-chay-v1/verify_documents.py`:
  UTF-8 không BOM/LF, liên kết local và hợp đồng tĩnh từ source đạt exit0.
- So sánh **1980 tệp** BE/FE và runner/compose với baseline trước ghi: giữ nguyên.
  Phạm vi hash loại dependency, cache, output và tệp `.env`; không đọc/công bố
  giá trị secret. Không sửa `.env` trong phiên.
- Bốn index được chèn có phạm vi, so hash trước ghi và kiểm bytes lịch sử giữ
  nguyên sau khi loại đúng đoạn mới; bằng chứng trong artifact của phiên.

Receipt/parser/hash lưu ở `storage/artifacts/context683-huong-dan-chay-v1/`
(Git ignore), không đưa credential hay corpus vào báo cáo.

**NOT RUN:** test/build ứng dụng, cài dependency, khởi động/restart dịch vụ,
migration DB, reindex, SSO, inference/model thật, deploy, commit/push. Kiểm tra
tĩnh không chứng minh môi trường của người vận hành đã chạy thành công.

## Bàn giao

Người vận hành chọn đúng cách nạp cấu hình tại phần1; môi trường mới theo
phần2–5 trước. Chưa tự sửa runner legacy hay compose V1 vì ngoài yêu cầu viết
tài liệu. Các kết quả test348FE/655BE ở phiên trước chỉ là lịch sử, không chạy
lại hoặc báo PASS mới trong phiên này.

[Snapshot683](../memory/snapshots/2026-10-27_session_683.md).
