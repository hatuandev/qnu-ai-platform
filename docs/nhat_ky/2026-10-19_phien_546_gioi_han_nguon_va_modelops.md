# Phiên 546 — Giới hạn nguồn và kiểm chứng ModelOps

## Phạm vi và kết quả

Thực hiện prompt đợt 2 trên các thay đổi đợt 1 chưa commit. Không thay parser,
Markdown Standard, retrieval hoặc phép tính. Chưa hoàn tất toàn đợt 2: provider
đã trả output thật nhưng proposal không qua validator bằng chứng; không có
proposal thật để người dùng duyệt, không có human approval hoặc live apply.

Ngoại lệ được người dùng xác nhận giữa phiên: đổi mặc định chat development
sang primary `cx/gpt-6-luna` qua **9router**, fallback `qwen3.5-9b` qua **QNU AI
Server (RTX 5090 - vLLM)**. Đã xác minh cả hai model có trong provider đang hoạt
động, lưu bằng service ModelOps và đọc lại. Chỉ thay các trường default chat và
chat chain; embedding/OCR/reranker giữ nguyên. Không đổi endpoint, credential,
provider enablement, timeout hoặc production policy. Bằng chứng cấu hình đã
che bí mật: `backend/storage/annotation546-chat-config.json`.

## Nguyên nhân và cách sửa

Guard cũ dùng `unresolved_cell_count` nên chưa phân biệt công việc chưa xong với
giới hạn nguồn đã được đối chiếu. Không xóa guard này. Thêm `limitations` vào
payload proposal, tách khỏi cell state; mỗi mục giữ row/column/raw, exact quote,
evidence unit, danh sách đơn vị đã kiểm tra và basis. Nguồn nói rõ chưa có nghĩa
khác với người duyệt đã kiểm tra một phạm vi nhưng chưa tìm thấy định nghĩa.
Đề xuất của model không tự chứng minh trường hợp thứ hai.

Tái dùng snapshot/authority/rebuild đợt 1. API có hành động riêng
`acknowledged_limits`, `changes_requested`, `approved`, `rejected`, quyền update,
hash, source/revision và idle. Xác nhận giới hạn ghi audit và policy vào cùng
snapshot; không đổi raw/state/normalized, không xóa unresolved count. Rejection
và yêu cầu kiểm tra tiếp giữ bộ hiệu lực cũ. Trường `field_usage` mặc định rỗng
được loại khi tính manifest seal để giữ tương thích; fingerprint nhận cả cache
cũ chưa có trường này.

`evaluate_source_policy` có strict mặc định và acknowledged-limits evaluation
được chọn rõ. Đếm unknown/acknowledged/unfinished/blockers riêng; issues độc lập,
scope, page mapping và integrity không bị ô đã xem xóa mất. Đây chỉ là service
evaluation: `publication_enabled=false`; unknown guard cũ giữ nguyên và nguồn
có limitations còn bị chặn riêng. Không mở phục vụ có giới hạn trên production.

Facts non-present vẫn bị loại; không đổi blank, unknown hoặc không áp dụng thành
0. Giới hạn theo row fields và `SourceUnit.field_usage` tới chunks/seal. Consumer
row-answer thực tế từ chối dữ kiện định lượng có giới hạn, ngay cả khi row field
mất cờ nhưng unit còn giữ. Chưa có đường trả lời mô tả known unknown từ nguồn
được xuất bản có giới hạn. Test vẫn giữ số 0, ô trống, nghĩa “chưa công bố” trong
raw/quote, dash đúng scope và unknown sau rebuild.

Panel review hiển thị raw, evidence, phạm vi với nội dung từng đơn vị, trạng thái
sau quyết định và hệ quả xuất bản. Xác nhận giới hạn là hành động riêng; mở panel
không ghi dữ liệu. Có lựa chọn yêu cầu kiểm tra tiếp. Các test approval dùng actor
`TEST-reviewer546`, không phải người dùng thật.

## ModelOps và runner thật

DOCX mô phỏng An Minh, không phải dữ liệu QNU chính thức:
`docs/tai_lieu/tuyen_sinh/tai_lieu_phuc_tap_kiem_thu_qnu_rag (1).docx`.
SHA-256 `58b3f7806529e4e506a6e2569a83ac688b8468fba955d0fe6638444a02099274`.
Runner đọc cặp MD/JSON đã được pipeline tạo, xác minh raw Office resource hash,
rồi dựng lại projection bằng mã hiện tại; không đọc gold hoặc chèn đáp án.

Hai lần đầu bị chặn trước inference khi chưa sao chép đủ resource vào dossier
cô lập; đã dùng bản archive gốc từ regression vừa chạy, checksum khớp. Lần qua
ModelOps trước khi đổi default trả `ALL_PROVIDERS_UNAVAILABLE`: default trỏ
`prov_gemini` đang tắt. Không coi đó là timeout/quota hoặc failure của provider
khác chưa được chọn. Người dùng sau đó cho phép đổi đúng hai model trên ảnh.

Sau cập nhật có ba lần gọi có giới hạn: output đầu bị từ chối validation nhưng
chưa có metadata phân tầng; lần chẩn đoán xác nhận provider `custom`, model thực
trả `gpt-6-luna`, không fallback, 22.835 input/1.248 output tokens, lỗi mượn chứng
cứ ô bên cạnh. Bổ sung quy tắc generic vào prompt, giữ nguyên validator. Lần cuối
22.944 input/1.611 output tokens, inference thành công nhưng scope quote không
khớp source prose; `SEMANTIC_EVIDENCE_INVALID`, exit 1. Không lặp tiếp để tìm
output PASS. Chi phí do ModelOps trả lần chẩn đoán/lần cuối lần lượt 0,0041741 và
0,0044082 USD; đây không phải tổng chi phí phiên. Fallback chỉ được kiểm qua
mock contract; primary đã trả lời nên chưa có inference fallback thật.

Runner mới `backend/scripts/verify_semantic_modelops.py`: lỗi trả exit 1; workflow
chưa được người dùng duyệt trả exit 2. `--proposal-only` chỉ được exit 0 nếu riêng
bước proposal hợp lệ, trạng thái vẫn WAITING_FOR_REVIEW. Test phân biệt provider,
timeout, schema, evidence và pending. Runner cũ ignored `propose_rag544.py` đã sửa
exit 0 sai khi FAIL; không gọi lại runner cũ. Metadata lỗi không chứa body model,
API key, endpoint hoặc nội dung private. Hồ sơ thật cuối có source pair/resource,
canonical/before projection và báo cáo; **không có proposal được chấp nhận**, không
có annotation hiệu lực hoặc chunks sau human approval thật.

## Kiểm chứng

Lệnh và test IDs đầy đủ ở `backend/storage/annotation546-validation-report.json`,
JUnit và log cùng tiền tố `annotation546-`. Lệnh focused từ root dùng
`backend/.venv/Scripts/python.exe -m pytest -q` với các file trong báo cáo và
`--basetemp` dưới `backend/storage`; full chạy từ `backend` bằng
`.venv/Scripts/python.exe -m pytest -q`. Windows sandbox làm runtime async bị
treo nên dùng execution đã được tự động cho phép ngoài sandbox; không bỏ test.

- Preflight đợt 1 hiện tại: **211 PASS**, 44,79 giây.
- Tái hiện trước sửa: **3 FAIL/1 PASS**, 6,11 giây.
- Focused toàn phạm vi: **235 PASS**, 49,30 giây; sau bổ sung compatibility case,
  focused đợt 2 **25 PASS**, 12,41 giây. Full cuối bên dưới chứa case cuối.
- Ruff có phạm vi 13 file: PASS. Frontend behavior: **7 PASS**; build Vite +
  TypeScript PASS. Biome trên 5 file PASS với `--line-ending=lf` theo AGENTS,
  giữ config formatter CRLF hiện hữu; không sửa cấu hình chung.
- Full cuối: **FAIL — 13 failed, 2.248 passed, 17 skipped, 0 error,
  23 subtests passed**, 255,33 giây, exit 1. So exact IDs với full545 đã đo:
  trùng cả 13 lỗi, không failure ID mới. Full545 là baseline lịch sử; preflight
  đợt này chỉ chạy lại focused, không gọi nó là full baseline hiện tại.
- Lượt full đầu dừng ở 44% để thêm compatibility regression; không tính PASS.
- Các approval/DB roundtrip test tạo rows mới, service commit trong savepoint,
  outer transaction rollback; LocalStorage là file tạm thật. Không sửa nguồn
  hoặc active pointer có sẵn. Machine roundtrip `annotation546-test-roundtrip.json`
  ghi rõ TEST approval, snapshot, raw limits, policy và fingerprint.

Đọc lại cấu hình bằng session DB mới xác nhận chính xác chat chain hai model;
nguồn DOCX thử cũ `ks_rev_84c4950c9ce2` vẫn `review_required`, binding chưa có
active source. Bằng chứng chỉ đọc: `annotation546-fresh-config.json`.

Giới hạn: chưa QA browser desktop/mobile/light/dark, production S3, stress hai
connection hoặc phục vụ nguồn có giới hạn. Không có human approval thật; toàn
đợt 2 **BLOCKED**, không báo APPROVED/PASS. Không commit/push, restart, deploy,
reparse, approve nguồn cũ, index hoặc publish.
