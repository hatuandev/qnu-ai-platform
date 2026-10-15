# Phiên 465 — Bỏ theo dõi artifact sinh tự động trong Git theo phương án an toàn

## 1. Mục tiêu và phạm vi

Thực hiện dọn dẹp các artifact sinh tự động đang bị Git theo dõi trong kho mã nguồn QNU AI Platform theo đúng nguyên tắc an toàn, tuân thủ `AGENTS.md` và skill `qnu-clean-code-architect`. Không refactor mã ứng dụng, không sửa mã kiểm thử.

### Ràng buộc bắt buộc đã tuân thủ:
- **Giữ nguyên 100% `docs/tai_lieu`**: Không xóa, không di chuyển, không bỏ theo dõi và không thêm bất kỳ quy tắc ignore nào cho thư mục này.
- **Không xóa file vật lý**: Chỉ thao tác bỏ theo dõi Git qua `git rm --cached --ignore-unmatch`, toàn bộ file cục bộ trên đĩa được giữ nguyên vẹn.
- **Giữ mã nguồn và fixture**: Giữ toàn bộ test code, `conftest.py`, script, lockfile, cấu hình, fixture E2E và báo cáo tóm tắt XML.
- **Không đụng dữ liệu runtime**: Không chạm DB, MinIO, Qdrant, bản backup thật hay biến môi trường.
- **Không commit / push / rewrite**: Không commit, không push, không rewrite history, không đổi remote. Toàn bộ thay đổi bỏ theo dõi đang ở trạng thái staged để người dùng chủ động kiểm tra.
- **Bảo toàn thay đổi của người dùng**: Mọi thay đổi unstaged có sẵn trong working tree của người dùng được bảo toàn 100%.

---

## 2. Kết quả kiểm kê và thực hiện

Số liệu kiểm tra thực tế từ cây Git tại `HEAD 40c8c65`:

| Nhóm | Số file | Dung lượng (MiB) | Hành động | Ghi chú |
| --- | ---: | ---: | --- | --- |
| `backend/storage/pytest*/` | 1.929 | 76,36 | **Bỏ theo dõi (Staged)** | 69 thư mục test output (backups test, lock, payload tar, md review, xlsx matrix) |
| Log chạy lệnh ngoài `docs/tai_lieu` | 80 | 4,15 | **Bỏ theo dõi (Staged)** | 79 file trong `backend/storage/*.log` + 1 file `frontend-build433.log` |
| `tmp/` (renders, QA documents) | 13 | 1,43 | **Bỏ theo dõi (Staged)** | Ảnh render preview, PDF/DOCX kết quả QA tạm |
| **Tổng cộng đã bỏ theo dõi** | **2.022** | **81,95** | **Staged `git rm --cached`** | Giữ nguyên file vật lý trên máy |

### Các nhóm giữ lại và lý do:
1. **Helper script `tmp/qa_drafting_render.py` (1 file, 1,92 KB)**: Giữ theo dõi Git vì đây là script sinh mã/QA kiểm thử, không phải artifact rác.
2. **Log trong fixture E2E `backend/storage/e2e_fixtures/` (6 file, ~82 KB)**: Giữ theo dõi Git gồm `api_stderr.log`, `api_stdout.log`, `worker_stderr.log`, `worker_stdout.log` (run 341) và `frontend.stderr.log`, `frontend.stdout.log` (run 354) vì thuộc bộ fixture test E2E.
3. **Báo cáo kiểm thử XML `backend/storage/pytest*.xml` (5 file, ~918 KB)**: Giữ theo dõi Git các file tóm tắt kiểm thử lịch sử (`pytest441_*.xml`, `pytest443_*.xml`).
4. **`docs/tai_lieu/` (100% nguyên vẹn)**: Không có bất kỳ thay đổi nào.
5. **Thư mục bảo vệ**: `backend/tests/`, `backend/app/`, `frontend/`, `scripts/`, `data/`, `legacy/`, `storage/documents/`, `browser_tester/`, `configs_locked/` hoàn toàn không bị ảnh hưởng.

---

## 3. Cập nhật `.gitignore` có phạm vi rõ ràng

Bổ sung các quy tắc ignore cụ thể, không dùng wildcard rộng (`*.json`, `*.pdf`, `*.docx`):

```gitignore
# Test artifacts & temporary QA outputs (Phiên 464)
backend/storage/pytest*/
backend/storage/pytest*.xml
backend/storage/*.log
!backend/storage/e2e_fixtures/**
frontend-build*.log
tmp/drafting-document-qa.docx
tmp/drafting-document-qa.pdf
tmp/drafting-document-render/
tmp/pdfs/
```

- Kiểm tra bằng `git check-ignore --no-index -v`:
  - `backend/storage/pytest414_verified/test.json` -> khớp quy tắc ignore.
  - `frontend-build433.log` -> khớp quy tắc ignore.
  - `tmp/drafting-document-qa.docx` -> khớp quy tắc ignore.
  - `backend/storage/e2e_fixtures/341/api_stderr.log` -> KHÔNG bị ignore (`!backend/storage/e2e_fixtures/**`).
  - `tmp/qa_drafting_render.py` -> KHÔNG bị ignore.
  - `docs/tai_lieu/**` -> KHÔNG bị ignore.

---

## 4. Kiểm chứng sau thay đổi

1. **Kiểm tra index Git**:
   - `git diff --name-status --cached`: Đúng chính xác 2.022 file `D` (staged deletion khỏi index).
   - `git diff --name-only --cached docs/tai_lieu`: 0 file (trống).
   - Không có bất kỳ file `.py`, mã nguồn hay fixture cần thiết nào bị staged xóa.
2. **Kiểm tra tính toàn vẹn file cục bộ**:
   - Các file vật lý đọc được trước đó vẫn tồn tại trên ổ đĩa.
3. **Lưu ý quan trọng**:
   - Thao tác `git rm --cached` loại bỏ các file khỏi chỉ mục Git của commit tiếp theo nhưng **không làm giảm dung lượng lịch sử Git** (các commit cũ vẫn chứa blob). Để giảm lịch sử Git cần quy trình riêng (filter-repo / BFG) kèm sao lưu và đồng thuận độc lập.
