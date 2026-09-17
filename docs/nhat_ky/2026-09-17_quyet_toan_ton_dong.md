# Nhật Ký Làm Việc — 17/09/2026

## Tiêu đề: Quyết Toán Tồn Đọng — Lint Xanh, Batch-Approve, E2E 2 Chế Độ

### 1. Bối cảnh
Quét tồn đọng sau phiên #42: `npm run lint` đỏ sẵn ở HEAD (CRLF), artifacts test bị commit trái AGENTS 9.1, thiếu batch-approve, TC-01/TC-02 E2E gãy theo môi trường backend up/down.

### 2. Các Thay Đổi Kỹ Thuật Đã Thực Hiện
1. **Lint xanh lần đầu có kiểm chứng** (`frontend/biome.json`): thêm `"lineEnding": "crlf"` khớp chuẩn CRLF đã commit toàn repo (thay vì rewrite lịch sử); chuẩn hóa endings 4 file do phiên trước ghi LF; `biome check --write` 2 file lệch format. Kết quả: `npm run lint` exit 0.
2. **Tuân thủ AGENTS 9.1**: `git rm --cached` playwright-report/test-results/tsbuildinfo + thêm rules vào `.gitignore`.
3. **Batch-approve** (`knowledge/schemas|service|router`): `POST /documents/batch-approve` duyệt nhiều tài liệu, lỗi từng file không chặn cả lô, cộng dồn indexed_chunks.
4. **E2E chạy cả backend up/down**: TC-01 dùng locator `.or()` (tên seed BE hoặc tên mock offline); TC-02 bỏ assert cứng vào dữ liệu mock (tiêu đề demo, "10 chunks"), thay bằng assert cấu trúc (table + bộ đếm "Hiển thị X/Y"). Phát hiện nhờ backend người dùng đang chạy với dữ liệu thật.
5. Tests: +1 batch-approve partial-failure. Tổng **BE 109/109**, Suite 09 **4/4 ở cả 2 chế độ**.

### 3. Kết Quả Kiểm Thử (Verification)
- `uv run ruff check .`: 0 lỗi; pytest 109/109.
- FE: lint exit 0, typecheck 0, build ✓; Suite 09: 4/4 (offline) và 4/4 (backend up, dữ liệu thật).
- Còn lại (tùy chọn, ngoài Knowledge): kéo thả ROI, cross-encoder local.
