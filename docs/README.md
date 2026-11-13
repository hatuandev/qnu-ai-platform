# Bản đồ tài liệu QNU AI Platform

> **Nguồn sự thật về hiện trạng:** mã trong `backendV1/` và `frontendV2/`.
> Tài liệu chỉ là ngữ cảnh; khi mâu thuẫn, mã và test hiện tại thắng.

Bản đang chạy là **V1**: FastAPI/Python 3.12 (`backendV1/`) và React 19/Vite (`frontendV2/`),
API prefix `/platform/v1alpha1`, cổng local 8002/3002. `backend/`, `frontend/` và `frontendV1/`
của bản trước **không còn trong Git**; nếu máy cũ còn thư mục untracked thì đó chỉ là tàn dư,
không dùng làm căn cứ.

---

## 1. Đọc gì trước

| Mục đích | Tài liệu |
|---|---|
| Hiểu kiến trúc đang chạy | [architecture.md](./architecture.md) |
| Ranh giới module, quy tắc import | [backendV1/docs/architecture.md](../backendV1/docs/architecture.md), [module-boundaries.md](../backendV1/docs/module-boundaries.md) |
| Chạy local | [quy_trinh/38_huong_dan_chay_qnu_v1.md](./quy_trinh/38_huong_dan_chay_qnu_v1.md) |
| Triển khai server | [trien_khai/02_quy_trinh_trien_khai_dokploy.md](./trien_khai/02_quy_trinh_trien_khai_dokploy.md) |
| Luồng nghiệp vụ V1 | [quy_trinh/README.md](./quy_trinh/README.md) (nhóm 19–44) |
| Trạng thái phiên gần nhất | [memory/PROJECT_CONTEXT.md](./memory/PROJECT_CONTEXT.md) |

## 2. Quy ước phân loại

- **Tài liệu sống** — mô tả hệ thống đang chạy. Được sửa khi hành vi thay đổi. Gồm:
  `docs/README.md`, `docs/architecture.md`, `docs/deployment.md`, `docs/huong_dan_chay_local.md`,
  `docs/quy_trinh/` (nhóm 19–44 và các tài liệu `V1_*`, trừ các file đã dán nhãn lịch sử ngày 2026-11-13),
  `docs/trien_khai/`, `backendV1/docs/`, `docs/memory/PROJECT_CONTEXT.md`.
- **Tài liệu lịch sử** — giữ nguyên để truy vết, **không sửa nội dung**, chỉ được dán nhãn:
  `docs/nhat_ky/`, `docs/bao_cao/`, `docs/memory/snapshots/`, `docs/quy_trinh/` nhóm 01–18,
  `docs/ke_hoach/`, `docs/kiem_thu/`, `docs/adr/`, các file `docs/nhan_xet_*.md`,
  `docs/gop_y_*.md`.
- Tài liệu lịch sử trong `docs/quy_trinh/` (01–18, `smart_approval.md`) mở đầu bằng khối
  **"TÀI LIỆU LỊCH SỬ"**. Các tài liệu mô tả `frontendV1` hoặc harness E2E đã gỡ (`V1_*`,
  34–37, 45) được dán nhãn **"TÀI LIỆU LỊCH SỬ (từ 2026-11-13)"** ngay dưới tiêu đề; nội dung
  giữ nguyên, không dùng để kết luận hiện trạng. Các thư mục lịch sử khác (`nhat_ky/`, `bao_cao/`, `memory/snapshots/`,
  `ke_hoach/`, `kiem_thu/`, `adr/`) được nhận diện theo vị trí trong bảng §3. Nếu gặp tài liệu
  mô tả `backend/app/...`, `Next.js`, DAG/channels, PaddleOCR/Gemini mà không có nhãn, coi đó là
  thiếu nhãn và bổ sung — không dùng nội dung đó để kết luận hiện trạng.

## 3. Bản đồ thư mục

| Thư mục | Loại | Nội dung |
|---|---|---|
| `docs/quy_trinh/` | sống + lịch sử | 19–44 và `V1_*` là hiện hành, trừ các file đã dán nhãn lịch sử 2026-11-13; 01–18 là lịch sử bản cũ |
| `docs/trien_khai/` | sống | Docker/Dokploy V1, an toàn dữ liệu, backup |
| `docs/memory/` | sống + lịch sử | `PROJECT_CONTEXT.md` (sống) + snapshot theo phiên (lịch sử) |
| `docs/nhat_ky/` | lịch sử | hơn 650 nhật ký phiên; chỉ đọc để truy vết |
| `docs/bao_cao/` | lịch sử | báo cáo kiểm chứng theo context |
| `docs/ke_hoach/` | lịch sử | kế hoạch/lộ trình; trạng thái ghi tại thời điểm viết |
| `docs/adr/` | lịch sử | ADR-011/012 của bản cũ; quyết định V1 nằm trong `backendV1/docs/` |
| `docs/kiem_thu/` | lịch sử | bộ câu hỏi/kiểm thử cũ; V1 dùng `backendV1/tests` (harness E2E trình duyệt đã gỡ cùng frontendV1) |
| `docs/diagrams/` | sống + lịch sử | sơ đồ `quy-trinh-qnu-backendv1-2026-10-26*` là V1; HTML cũ là lịch sử |
| `docs/tai_lieu/` | dữ liệu | PDF/DOCX/MD nguồn để thử nghiệm, không phải tài liệu hệ thống |
| `docs/kien_truc/`, `docs/van-ban/` | trống | giữ chỗ, không có nội dung |

## 4. Quy tắc khi sửa tài liệu

1. Chỉ tài liệu sống mới được cập nhật theo hành vi mới; lịch sử giữ nguyên văn.
2. Mọi số liệu test/benchmark phải ghi rõ thời điểm, phạm vi và trạng thái
   PASS/FAIL/NOT RUN; không chuyển kết quả bản cũ sang V1.
3. Không đưa secret, credential, PII hoặc corpus nội bộ vào tài liệu.
4. Giữ UTF-8 không BOM, LF; đọc lại tiếng Việt sau khi ghi.
5. Đồng bộ memory theo [workflow-and-memory](../.agents/rules/workflow-and-memory.md)
   khi kết thúc task có thay đổi.
