# Phiên516 — Bản sạch thử cho PDF bảng52 ngành

## Trạng thái

**Đã lưu revision2 chờ duyệt trong app; chưa embedding/xuất bản.** Người dùng
cho phép chọn một nguồn hiện có lỗi bảng/OCR để làm sạch. Theo skill ingestion,
không tự coi output của agent là phê duyệt bởi con người. Đã gửi yêu cầu xác
nhận hai thay đổi cụ thể; chỉ mục thử sẽ làm sau khi người dùng duyệt nội dung.

## Chọn nguồn và bằng chứng

- Inventory22nguồn admissions: chọn PDF danh sách ngành2025, một trang,52hàng
  dữ liệu, có cảnh báo VISUAL_CONTENT_REVIEW và bản cũ đã duyệt qua Studio.
- Binding `bnd_58509a6c7f92`; source cũ `ks_rev_fafaaf1e6106`.
- DOC/PDFgốc giữ nguyên; SHA256
  `85ba8210be71e359d78aaa8b6efa9102adc53c4f098b685f21552c27c6cdd186`.
- Render toàn trang bằng Poppler và xem PNG. Nhìn đối chiếu xác nhận hai lỗi
  chữ ở tiêu đề và ô tên ngành dòngSTT52. Đã sửa theo ảnh, không dùng từ điển
  vá retrieval, không gọi model/OCR/cloud, không sửa số hay mã theo suy đoán.
- Chuyển tiêu đề dạng div HTML thành H1 Markdown để biểu diễn cấu trúc; giữ
  các ảnh/trang trí và tham chiếu cũ, không tự tạo URL public thay thế.
- Ledger giữ before/after, vị trí trang/hàng/cột và nguồn/hash; không giả bbox.

## Thay đổi thực trong app

- Gọi `source_ingestion_service.update_revision_content` với hash gốc,
  actor `codex-local-cli`, lý do và đường dẫn ledger. Không mượn ID cán bộ
  quản trị để giả người đã duyệt. Trường created_by của revision mới được ghi
  cùng actor thật của thao tác CLI; reviewer/approval không được đặt.
- Revision mới: `ks_rev_be5b393c11af`, revision_no2, status review_required.
- Canonical SHA256 mới:
  `86e6626bffef32c08bd69259a1a0391180e40ac0c0ed8b23e43e78f35a675128`.
- Canonical cũ giữ nguyên:
  `f096720b0d414129b5270933f2cdc3df176be224f65b34d1531b4b2edd81f7c2`.
- Giữ52dòng,52facts, toàn bộ STT/mã ngành, multiset số và mọi ô khác. Chỉ ô tên
  dòng52 đổi chữ. Preview cấu trúc65đoạn, không phải index/vector runtime.
- Source/block/bbox/ảnh gốc giữ qua revision cũ và snapshot; layout text alignment
  của bản hiệu đính đánh dấu stale, không coi bbox cũ là text mới đã căn chỉnh.
- Manifest hiện có dùng kind `table` cho cả header và hàng, không phải `table_row`.
  Kiểm tra trạng thái cho53non-container table units (gồm header): cũ unknown,
  mới proposed; không tự chuyển thành verified hoặc lấy năm từ tên tệp.

## Quality gate và phê duyệt

Ba cảnh báo được giữ nguyên, không sửa guard để làm xanh:

- VISUAL_CONTENT_REVIEW: ảnh/trang trí của nguồn cần xem.
- CONTENT_WORDING_CHANGED: hai chỗ sửa chữ cần duyệt theo nguồn.
- CONTENT_FORMULAS_REDUCED: heuristic đếm dấu `=` cả trong thuộc tính HTML.
  Ở lần đổi div thành heading, mất một dấu `=` của style, không có công thức
  toán trong vùng bị thay. Đây là hạn chế detector được ghi lại, không phải
  căn cứ tự bỏ gate hoặc phê duyệt toàn tài liệu.

Thử gọi chunk-set service đúng revision nháp: bị từ chối
`SOURCE_REVISION_NOT_READY` như thiết kế. Không ép status ready hoặc bypass
review để dựng vector. Yêu cầu người dùng duyệt cụ thể đã gửi trong chat.

## Artifact và bảo toàn

S3StorageDriver prefix:
`snapshots/markdown-trials/516/bnd_58509a6c7f92/`

Từng object được đọc lại và đối chiếu SHA256:

- `before.json`: full source snapshot và pointers của22bindings;
  hash `3ee6ff6ca135e5e8bfbaa32f2e45fb7dfaf886e0635a22b2055f5d6a5cc75d51`.
- `before.md`, `source.pdf`, `source-page.png`: raw/reference nguyên vẹn.
- `corrections.json`: ledger, hash
  `f820b200852c0ec098aeabb3ee30bbe9f9ca2832cb9eed2409bc7a83e65ecf3f`.
- `candidate.md`: file nháp local có newline cuối, hash khác canonical server
  vì server normalize trailing newline; không coi hai hash là cùng bytes.
- `chunk-preview.json`: preview cấu trúc, không có vector hoặc seal xuất bản.
- `report.json`: status DRAFT_SAVED_REVIEW_REQUIRED,
  hash `863112b4f6925becf5b0e622208a28555f42c1cbaae07c8b78e7fd3d00e6d92f`.

Cache xem tại `backend/storage/md516/`; Markdown tạo bằng apply_patch. Không
commit artifact/corpus. Đã yêu cầu mở đúng revision2 trong webUI, công cụ trả
queued; không coi là đã nghiệm thu UI.

Đối chiếu cuối: mọi source/index/epoch/status phục vụ của22bindings không đổi,
collection epoch4. Chỉ thêm revision nháp, không tạo tài liệu/binding trùng.

## Kiểm chứng thực chạy

- CWDbackend, `.venv/Scripts/python.exe -`: inventory, source/hash snapshot,
  ledger/number/table invariant checks, update revision service, preview65đoạn,
  review-gate rejection và serving-state comparison, exit0/PASS.
- CWDrepo: `pdftoppm -f 1 -singlefile -scale-to 2200 -png
  backend/storage/md516/source.pdf backend/storage/md516/source-page`, exit0;
  ảnh đã xem toàn trang. PDFkhông bị sửa.
- Lần đọc ban đầu stdout cp1252 không in được tiếng Việt, exit1 trước ghi;
  chuyển stdout UTF8 rồi chạy thành công. Không đổi encoding file để che lỗi.
- Không production-code change; không chạy fullpytest/build cho artifact và
  tác vụ vận hành này. UTF8/LF/link/diff docs kiểm tra trước bàn giao.
- Embedding, retrieval A/B, sinh/chấm đáp án: **NOT RUN**, do bản sửa cần duyệt.
  Không tuyên bố RAG cải thiện hoặc thay thế benchmark82câu.
- Không reset/seed/restart/deploy/Git, không sửa model/prompt/Top K; không xóa
  `docs/tai_lieu`, không gửi nguồn ra ngoài. Skill evaluation giữ chấm chất lượng
  tách biệt khỏi kiểm tra toàn vẹn/chỉnh chữ.

## Cần tiếp tục

Sau xác nhận nội dung của người dùng: ghi review thật với dấu vết ủy quyền,
dựng staging đúng source revision này bằng provider nội bộ; so cùng cấu hình/
snapshot chỉ thay một binding, kiểm tra nguồn/năm/trích dẫn trước khi xuất bản.
Không tự thay active trong khi chưa có sự phê duyệt.
