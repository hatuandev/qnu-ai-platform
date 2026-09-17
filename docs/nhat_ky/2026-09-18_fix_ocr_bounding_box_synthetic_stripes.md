# Nhật Ký Làm Việc — Sửa Lỗi OCR Bounding Box Nát Bét Trên PDF

- **Ngày**: 2026-09-18 00:13 (UTC+7)
- **Phiên**: #74
- **Mục tiêu**: Sửa lỗi OCR bounding box (khu nhận diện) hiển thị nát bét khi upload file PDF trong Document Verification Studio

---

## 1. Vấn Đề

Upload file PDF `4740-qd-bgddt-bo-chi-so-cds-dai-hoc.pdf` (Quyết định về bộ chỉ số CĐS đại học), mở Studio đối soát thấy:
- **Bounding boxes thành dải sọc ngang**: Mỗi dòng markdown = 1 khối ngang `x=8.0, width=84.0`, cách đều `step_y` pixel
- **Badge hiển thị markdown thô**: `**bộ giáo dục và đào tạo**`, `# **quyết định**` — không phải nhãn ngữ nghĩa sạch
- **Trang landscape (bảng biểu) bị cắt nát**: Dải sọc ngang cắt chéo qua bảng hoàn toàn sai geometry

File `.docx` scan tốt vì đi qua luồng `_ensure_page_blocks` → `SmartLayoutDetector` thật.

---

## 2. Nguyên Nhân Gốc Rễ

1. **[`backend/app/modules/ocr/adapters/mistral_adapter.py`](../../backend/app/modules/ocr/adapters/mistral_adapter.py)** (lines 113-140):
   - Vòng lặp tạo khối giả: `blocks.append({"x": 8.0, "width": 84.0, "label": clean_line[:40]})`
   - Không gọi `SmartLayoutDetector` — chỉ tạo geometry giả từ markdown text

2. **[`backend/app/modules/knowledge/service.py`](../../backend/app/modules/knowledge/service.py)** `_is_stale_raw_blocks`:
   - Kiểm tra `has_semantic = type in ('title', 'header')` → khối giả có type `title`/`header` → trả `False`
   - `_ensure_page_blocks` không bao giờ re-extract geometry thật

3. **[`frontend/src/components/admin/document-bounding-visualizer.tsx`](../../frontend/src/components/admin/document-bounding-visualizer.tsx)** (line 322):
   - Render `{box.label}` verbatim → badge hiển thị 40 ký tự markdown thô

---

## 3. Thay Đổi Kỹ Thuật

| Tệp | Hành Động | Mô Tả |
|---|---|---|
| [`mistral_adapter.py`](../../backend/app/modules/ocr/adapters/mistral_adapter.py) | **Sửa đổi** | Thay thế vòng lặp blocks giả bằng `SmartLayoutDetector` thực: (a) PDF → PyMuPDF pixmap 150dpi + hybrid layout detection per page; (b) Image → OpenCV decode + detect; (c) Fallback: `blocks = []` |
| [`knowledge/service.py`](../../backend/app/modules/knowledge/service.py) | **Sửa đổi** | `_is_stale_raw_blocks`: Phát hiện synthetic blocks (`x≈8.0, width≈84.0` hoặc `**`/`#` trong label) → return `True` → auto re-extract |
| [`document-bounding-visualizer.tsx`](../../frontend/src/components/admin/document-bounding-visualizer.tsx) | **Sửa đổi** | `REGION_BADGE_LABELS` map + `getDisplayBadge()` + badge `max-width: 120px, text-overflow: ellipsis, pointer-events: none` |
| [`workflows/router.py`](../../backend/app/modules/workflows/router.py) | Auto-fix | Ruff sắp xếp imports alphabetically |
| [`workflows/service.py`](../../backend/app/modules/workflows/service.py) | Auto-fix | Ruff sắp xếp imports alphabetically |

---

## 4. Xác Minh Trực Tiếp

Chạy script kiểm tra trên document `doc_d12f90421e2d`:
- `_is_stale_raw_blocks` → `True` (phát hiện blocks giả cũ)
- Sau `get_studio_view`:
  - **Page 1**: 16 boxes — header, title, text, list (coordinates chính xác)
  - **Page 4**: 4 boxes — `table` (21.4%, 8.9%, 64.5%, 79.5% bao trùm bảng ngang), `signature` (dấu đỏ), `text`
- DB đã commit blocks mới thay thế blocks giả

---

## 5. Kết Quả Kiểm Thử

```
uv run ruff check .           → ✅ All checks passed!
uv run --extra dev pytest -v  → ✅ 143/143 passed in 54.94s
npm run lint                  → ✅ 0 lỗi (90 files)
npm run typecheck             → ✅ 0 lỗi
npm run build                 → ✅ thành công (11.52s)
```
