# NHẬT KÝ LÀM VIỆC — PHIÊN #222
**Ngày**: 2026-09-25 | **Thời gian**: 23:40 (UTC+7)
**Tiêu đề**: Fix Worker Build Dokploy Thiếu README.md (Hatchling Editable Install)

---

## 1. Bối Cảnh & Triệu Chứng
- Deploy Dokploy `demo-ai-platform-9hzwjj`: clone ✅, frontend ✅ (cached), backend deps ✅ (142 packages / 1102s).
- Worker chết tại step 12/13 `uv pip install -e . --no-deps`:
  `OSError: Readme file does not exist: README.md` (hatchling `validate_fields`), exit 1.

## 2. Nguyên Nhân Gốc
- `backend/pyproject.toml:5` khai báo `readme = "README.md"` → hatchling bắt buộc file tồn tại khi build editable.
- `backend/Dockerfile` bước 6 chỉ COPY `app/`, `alembic/`, `alembic.ini`, `entrypoint.sh` — thiếu `README.md`.
- `backend/.dockerignore` không loại trừ `README.md` nên file có sẵn trong context, chỉ cần COPY thêm.
- Cả 2 service `backend` + `worker` dùng chung 1 Dockerfile → 1 fix bao cả 2. Frontend deploy build từ `./frontend2`.

## 3. Thay Đổi
- `backend/Dockerfile`: thêm `COPY README.md ./README.md` ngay trước bước 6b.
- Verify: `git diff` đúng 1 dòng; `Test-Path backend/README.md` = True; `.dockerignore` cho phép.

## 4. Lưu Ý Redeploy
- Rebuild sẽ nhanh vì layer deps đã cached (không đổi `pyproject.toml`).
- Không chạy được `docker build` local để kiểm chứng (cần daemon + ~20 phút); lỗi cũ mang tính quyết định (deterministic) nên COPY là đủ.
