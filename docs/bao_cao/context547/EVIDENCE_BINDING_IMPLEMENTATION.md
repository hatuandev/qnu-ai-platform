# Evidence Binding — phiên 547

## Luồng và phạm vi

API hiện hữu xác minh quyền, draft/idle, binding/revision và cặp MD–JSON;
`proposal_base` dựng nguồn gốc cùng enrichment đã ghim. ContextBuilder đối chiếu
Structured Document với manifest đã seal, text, raw/state và provenance. ModelOps
trả selectors; backend bind vào `SemanticAnnotations` hiện có, rồi stage một lần
sau khi tất cả gói hợp lệ. Pending không sửa graph/facts/raw hoặc dữ liệu phục vụ.

Các file mới trong `backend/app/modules/knowledge/services/`:

| File | Trách nhiệm |
|---|---|
| `semantic_evidence.py` | Authority check, exact source slice, identity/hash/span |
| `semantic_context.py` | Local/related context, row windows/directory, bounded expansion |
| `semantic_binding.py` | Strict selectors → annotations; coordinate và scope guards |
| `semantic_modelops.py` | Existing inference route, budgets, metrics và atomic staging |

Tích hợp tối thiểu trong `semantic_annotations.py`, `source_limitations.py`,
`unit_annotation.py`, `qnu_serving.py` và runner `verify_semantic_modelops.py`.
UI review/types hiện có thêm reason, source unit, span và trường hợp thiếu căn cứ.
Không thêm resolver, database table, persistence hay endpoint model riêng.

## Bằng chứng nguyên văn

Model chỉ chọn `context_id`, `evidence_id`, `source_unit_id`, đối tượng đích,
scope và reason. Schema cấm model gửi quote/raw/offset tự viết. Backend tra registry
của chính gói đã cấp và cắt nguyên văn từ source unit hoặc raw cell đã xác minh.

Binding lưu source document/revision, hash cặp nguồn, input hash, unit/column,
SHA-256 của toàn text gốc và khoảng `[start,end)` theo **Unicode code points**.
Python slicing dùng chính hệ tọa độ này; không trộn UTF-16 hay byte offsets.
Backend tái tạo binding và evidence ID, kiểm tọa độ/hashes và exact quote trước khi
chạy validator cũ. Không fuzzy match, sửa dấu, thêm từ, nối units hay đổi unit.
Lookup nhãn tham chiếu có NFC/casefold/whitespace; thao tác đó không áp vào evidence.

Legacy annotation không có binding tiếp tục qua exact-quote validators cũ; không
viết lại hash snapshot cũ. Snapshot/pointer/history/replay đợt 1 vẫn là authority
duy nhất. Replay thực từ PostgreSQL test và LocalStorage qua session khác đã được
kiểm, không gọi model lại. Chính sách strict/unknown/acknowledged-limits đợt 2 giữ
nguyên; UI không cấp quyền xuất bản.

## Context và thiếu căn cứ

- Mỗi bảng giữ đầy đủ header paths, column IDs, raw/state và cửa sổ dòng.
  Row directory toàn bảng chứa ID/identifier nguồn để note group có thể trải
  qua nhiều cửa sổ; cell meaning vẫn cần field đầy đủ trong gói đang thấy.
- Local gồm heading, trước/sau bảng và header. Context refs/parent hoặc nhãn
  cấu trúc chính xác duy nhất dẫn tới related units. Row labels số không được
  biến thành tham chiếu tài liệu. Nhãn trùng/missing refs ghi trace.
- Ưu tiên local trước remote. Nếu remote khiến gói vượt budget, giữ ID trong
  `deferred_related_unit_ids`, không khai đã đọc chúng; proposal giữ unresolved
  cần người đối chiếu. Khi phân tích cả tài liệu, prose đó còn có gói riêng.
- `needs_context` chỉ nhận ID thực, có visited set/round/unit/call/byte limits.
  Yêu cầu thêm dòng phải nạp đúng fields vào table view, không chỉ text GFM.
  Hết budget, cycle/no-new hoặc ID sai đều dừng; không tạo quan hệ thay thế.
- Đối tượng focal chưa được cấp vì packet/count budget làm toàn lượt thất bại
  trước inference. Lượt lỗi sau một gói cũng không stage nửa bộ annotations.

`SemanticContextPolicy` nằm trong policy annotation hiện hữu; không sửa cấu hình
ModelOps DB. Defaults: packet 48.000 bytes (gồm system/schema),
24 packets/calls, 120 units, 2 expansion rounds; tổng mặc định 1.000.000 bytes.
Schema ràng buộc giới hạn cấu hình. Kiểm tổng tối thiểu trước inference tránh
tiêu phí một phần ngân sách rồi mới nhận ra không thể hoàn tất các gói ban đầu.

## Giới hạn ngữ nghĩa và review

Exact quote chỉ chứng minh sự tồn tại. Guard cơ học từ chối năm cột trái năm trong
span, row code ngoài tập/range đã nêu, sibling evidence và target ngoài context.
Span trộn nhiều năm hoặc nhiều mã cho scope một dòng phải chọn hẹp hơn; backend
không đoán đâu là mệnh đề phủ định. Đây không phải bộ hiểu ngôn ngữ tự động hoàn
chỉnh: negation, điều kiện pháp lý và unique association vẫn cần người có quyền
đối chiếu toàn source unit, reason và scope. Không dùng confidence để tự duyệt.

Không thay default primary/fallback. Inference sử dụng ModelOps hiện tại, gồm
timeout/retry/quota/accounting. Dossier thật được chạy với cấu hình/credential
mã hóa sao chép READ ONLY sang DB test; không ghi health/quota vào DB ứng dụng.

Kết quả, exact test IDs và giới hạn live ở [VALIDATION_REPORT](VALIDATION_REPORT.md).
