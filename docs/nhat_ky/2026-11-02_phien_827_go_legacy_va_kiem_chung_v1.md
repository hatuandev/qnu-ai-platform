# Phiên 827 — Gỡ backend/frontend legacy và kiểm chứng V1

## Yêu cầu và bảo toàn dữ liệu

User đã push phiên trước, yêu cầu xóa hai thư mục legacy rồi kiểm tra V1. Trước thao tác, working tree sạch tại commit `6e010471` trên nhánh `v1.0.3`. Không fetch/push hoặc thay nhánh. Không thấy tiến trình dùng hai đường dẫn legacy; cổng V1 cũng trống trước kiểm tra.

Đã chuyển nguyên hai thư mục sang bản lưu riêng ngoài checkout, cùng ổ đĩa:

`D:/DuAnPhanMem/qnu-ai-platform-legacy-archive-20261102-214426/`

Trong repo không còn `backend/` hoặc `frontend/`. Đối chiếu đủ 1.799 tệp được Git theo dõi trong bản lưu; các tệp ignored, storage, cấu hình và thư viện cũ cũng được giữ do chuyển nguyên thư mục. Hash hai tệp cấu hình riêng khớp trước/sau; không đưa nội dung/key vào báo cáo. Thư mục lưu có ACL riêng cho người dùng hiện tại và SYSTEM. Đây là gỡ khỏi checkout, không phải xóa bản lưu để giải phóng ổ đĩa.

Trước di chuyển đã kiểm đường dẫn tuyệt đối chính xác và không phải reparse point. Hai lần chuẩn bị ban đầu vướng Split-Path/ACL không canonical, chưa di chuyển dữ liệu; đã dùng đường dẫn .NET và ACL mới rồi hoàn thành. Không thay đổi `.env` gốc, DB, Docker volume, object store hoặc worktree `tmp/release-v1.0.3`.

## Kiểm chứng sau khi gỡ mã cũ

| Phạm vi | Kết quả thực chạy |
| --- | --- |
| Backend V1 đầy đủ | **1.306/1.306 PASS**, không fail/error/skip; exit0, 1.239,09 giây |
| Đối chiếu JUnit | Đúng 1.306 node đã collect, không thiếu/trùng/unknown |
| DB thử | Bốn DB riêng, migration V1; sentinel và version legacy giả giữ nguyên; cả4DB đã dọn, còn0 |
| Frontend Vitest | **701/701 PASS**, 80 suites; exit0,58,52giây |
| Frontend build/TypeScript | PASS; còn cảnh báo kích thước bundle, không sửa UI để che cảnh báo |
| Runner | **52 tests PASS**, exit0 |
| Docker | Config validation và build backend/frontend V1 PASS khi hai thư mục cũ đã vắng |
| Preflight thật | Redis/PostgreSQL schema/Qdrant/S3 readonly/Vite đềuOK |
| Khởi động thật | API readiness200, OpenAPI xác nhận Backendv1, worker chạy trên queue thử riêng |
| Trình duyệt | UI V1 HTTP200, dashboard hiển thị;0pageerrors, screenshot đã đối chiếu |

Bộ backend dùng runner cục bộ `tmp/remove827/run_backend.py`, chia file không trùng thành4nhóm trên DB/queue/cache riêng; chặn AI egress, Selector loop cho3nhóm Windows và Proactor cho recovery. Không sửa test/assertion để làm PASS, không retry model. Summary exact `tmp/remove827/backend/summary.json` và receipt từng nhóm là bằng chứng.

Live smoke chỉ đọc UI/API trên dữ liệu hiện có; worker dùng queue ngẫu nhiên riêng và OWN_RECONCILE=false để không tự xử lý công việc đang chờ. Sau kiểm tra đã dừng đúng cây tiến trình của phiên thử, cổng8002/3001 trống. Đã dọn4key Redis smoke và3key namespace backend test, còn0, không flush DB/cache dùng chung.

Script đo live có lỗi ban đầu: giả định service name cố định trong khi `.env` đặt nhãn khác; sau đó gặp cơ chế launcher Windows khi dừng, và giải mã stdout Node bằng CP1252. Đã giữ log và sửa riêng harness: xác nhận bằng OpenAPI thay nhãn cấu hình, dừng cây tiến trình còn sở hữu, đọc UTF-8. Không sửa app/config để ép kết quả xanh. Không có OCR/LLM call, publication hoặc reindex trong smoke.

## Tài liệu và bàn giao

Đổi đường dẫn hiện hành trong AGENTS, bảng kiểm chứng, sáu skill chuyên ngành và hướng dẫn root/backend/deploy; giữ nguyên lịch sử, bất biến quyền V1 và chuỗi migration legacy. Không chỉnh module nghiệp vụ V1.

Artifacts nằm ở `tmp/remove827/`: archive receipt, log test/build, summary exact, ảnh `v1-ui.png`, preflight, live checks và cleanup receipt. Source corpus và key không vào Git.

Chưa commit/push lần gỡ này. User có thể chạy:

```powershell
.\make.ps1 check
.\make.ps1 dev
```

Giao diện3001/API8002. Không cần migration lại vì preflight xác nhận schema current. Chưa chạy lại bài hỏi đáp/OCR bằng model thật; kết quả này xác nhận V1 chạy và bộ test đạt độc lập với hai thư mục legacy. Tồn đọng ModelOps/E2Eprofile Nemotron phiên825 vẫn là việc riêng, không phải phụ thuộc mã legacy và không được đổi trong đợt xóa này.
