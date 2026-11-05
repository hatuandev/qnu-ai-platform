# Phiên 881 — Chuẩn hóa tài liệu về V1, dán nhãn lịch sử

## 1. Yêu cầu

Người dùng yêu cầu cập nhật tài liệu sang V1 để tránh nhầm lẫn giữa bản `backend/` +
`frontend/` cũ và hệ thống đang chạy ở `backendV1/` + `frontendV1/`. Phạm vi là tài liệu
sống; không viết lại lịch sử.

## 2. Giả định và phạm vi

- Nguồn sự thật là mã trong `backendV1/` và `frontendV1/`; tài liệu chỉ là ngữ cảnh.
- `docs/nhat_ky/`, `docs/bao_cao/`, `docs/memory/snapshots/` là lịch sử, giữ nguyên văn.
- Không sửa mã ứng dụng, migration, cấu hình hay dữ liệu; không gọi model, không restart,
  không publish, không push.
- Chỉ dán nhãn cho tài liệu lịch sử; nội dung lịch sử không bị chỉnh.

## 3. Thay đổi

**Tạo mới**

- `docs/README.md`: bản đồ tài liệu, phân loại "sống" và "lịch sử", quy tắc đọc/sửa và
  bảng thư mục.

**Viết lại cho đúng V1**

- `docs/architecture.md`: thay bản mô tả Next.js/`/channels`/DAG/5 trợ lý/PaddleOCR-Gemini/
  Structured Fact Layer bằng kiến trúc V1 thật: modular monolith 16 domain, 4 tầng
  `api/platform/ports/adapters`, 53 bảng và 14 migration, luồng 8 bước, bảng năng lực
  đã có/chưa có. Giữ phần định hướng 5 lĩnh vực nhưng ghi rõ là mục tiêu, không phải
  tính năng đã triển khai.
- `docs/quy_trinh/README.md`: đưa 19–44 và các tài liệu `V1_*` lên mục "V1 hiện hành";
  chuyển 01–18 và `smart_approval.md` xuống mục "Lịch sử" có ghi chú; thay khối
  "nguyên tắc vận hành" cũ (MinIO-First, Gemini fallback) bằng liên kết tới bảng kiểm chứng.

**Dán nhãn lịch sử (chỉ thêm khối đầu trang)**

- 19 tài liệu: `docs/quy_trinh/01…18_*.md` và `docs/quy_trinh/smart_approval.md`.
- `docs/adr/ADR-011` và `ADR-012`: thêm dòng "Hiệu lực với V1: KHÔNG ÁP DỤNG" vì mô hình
  `repository`/`/documents` đã bị loại bỏ khỏi V1; lịch sử quyết định giữ nguyên.

**Sửa câu đã lệch**

- `docs/quy_trinh/38_huong_dan_chay_qnu_v1.md`: bỏ câu nói `run.ps1` vẫn chạy bản cũ
  (`run.ps1` nay gọi lại `make.ps1`); nêu rõ `backendV1/docker-compose.v1.yml` là entrypoint
  tương thích và thư mục legacy untracked trên máy cũ không dùng làm căn cứ.
- `HUONG_DAN_CHAY_LOCAL.md`: bổ sung ghi chú thư mục legacy còn untracked, trỏ về bản đồ tài liệu.
- `docs/trien_khai/README.md`: thêm phạm vi V1, sửa cổng backend trong sơ đồ `8001 → 8002`.
- `docs/ke_hoach/README.md`: ghi rõ thư mục là tài liệu lịch sử, trạng thái theo thời điểm viết.

## 4. Phương pháp

Đối chiếu từng câu tài liệu với mã: `docker-compose.yml` (context `backendV1`/`frontendV1`),
`api/wiring.py`, `modelops/registry.py`, `modelops/public_api.py`, `quy_trinh/38`, `run.ps1`.
Xác định tài liệu nào sống, tài liệu nào lịch sử bằng cách kiểm tra đường dẫn và nội dung mô tả.
Thêm nhãn bằng script bảo toàn nội dung và kiểu xuống dòng sẵn có của từng tệp.

## 5. Kiểm chứng đã chạy

| Kiểm tra | Kết quả |
|---|---|
| `git status --short` | 27 tệp sửa + 1 tệp mới; không có tệp mã nguồn nào thay đổi |
| Kiểm link tương đối trên 9 tệp tài liệu sửa chính | 0 link hỏng |
| Kiểm link trên 3 tệp index memory (`WORK_LOG`, `nhat_ky/README`, `PROJECT_CONTEXT`) | **257 mục hỏng sẵn** (trỏ tới `backend/`, `frontend/` đã gỡ và một số nhật ký cũ không còn tệp); không sửa trong phiên này |
| Kiểm BOM trên toàn bộ tệp tài liệu đã sửa | 0 tệp có BOM |
| Đọc lại tiếng Việt các tệp mới/sửa | Đúng nội dung, không mojibake |
| Ruff / Pytest / Vitest / build | **NOT RUN** — thay đổi chỉ là tài liệu; bảng kiểm chứng không yêu cầu chạy ứng dụng |

Link của phiên này (881 trong `WORK_LOG`, `nhat_ky/README`, `PROJECT_CONTEXT`, snapshot) đều
phân giải đúng; các mục hỏng nằm ở dòng lịch sử có từ trước. Script kiểm link là công cụ tạm,
gặp một liên kết chứa ký tự đặc biệt không phân giải được, nên con số 257 là xấp xỉ theo các
mục đọc được, không phải kiểm kê tuyệt đối.

Không chạy migration, không gọi model, không restart dịch vụ, không đổi dữ liệu.

## 6. Ghi nhận ngoài phạm vi

- `docs/huong_dan_chay_local.md` đang được sửa đồng thời trong working tree (nội dung mở rộng
  hướng dẫn local). Phiên này **không sửa** tệp đó và giữ nguyên thay đổi chưa commit.
- `core.autocrlf=true` trên máy Windows làm working copy dùng CRLF dù index giữ LF; 19 tệp
  lịch sử vốn đã CRLF nên nhãn được chèn theo CRLF để tránh diff toàn tệp.
- Chưa dán nhãn cho các tệp đánh giá cũ ở `docs/nhan_xet_*.md`, `docs/gop_y_*.md`,
  `docs/kiem_thu/`, `docs/diagrams/*.html`; chúng đã được liệt kê là lịch sử trong
  `docs/README.md`.
- Các link lịch sử hỏng (257 mục xấp xỉ) trỏ tới `backend/`, `frontend/` và nhật ký cũ đã bị gỡ;
  sửa chúng cần đối chiếu bản lưu ngoài checkout, không thuộc phạm vi phiên này.

## 7. Bước tiếp theo

1. Rà `docs/trien_khai/01_cong_nghe_ha_tang.md` và `03_an_toan_du_lieu_va_van_hanh.md` xem còn
   cổng/stack legacy không.
2. Dán nhãn hoặc chuyển sang kho lưu trữ lịch sử cho 9 tệp `docs/nhan_xet_*.md`.
3. Lập kế hoạch riêng cho link lịch sử hỏng trong `WORK_LOG`/`PROJECT_CONTEXT`: thay bằng ghi chú
   "tệp đã gỡ" hoặc trỏ về bản lưu, không để link chết.
4. Cân nhắc thêm kiểm tra link Markdown vào CI khi CI được dựng.
