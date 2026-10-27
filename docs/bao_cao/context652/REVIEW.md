# Context652 — Review ngữ nghĩa sau Compiler backendV1

## Phạm vi

Người dùng yêu cầu triển khai một lượt review sau Compiler để tìm ý bị bỏ sót
hoặc diễn giải sai. Giữ phạm vi chỉ backendV1 từ xác nhận trước; không sửa FE,
không gọi model trên corpus thật, không migrate phục vụ hoặc restart.

Module mới `knowledge/compilation/review/` cung cấp một request review độc lập,
có input/draft/bundle pin, coverage hai chiều và báo cáo nguyên văn. Caller gọi
POST sau Compiler completed; worker Compiler không tự phát sinh request trả phí.
Không sửa draft, auto repair/approve/pub/index; giữ API cũ và trạng thái
semantic_faithfulness=not_evaluated của draft gốc.

## Thay đổi

- schemas/models/material/report/artifacts/service/execution/router trong module
  mới, không sửa service/execution/drafting Compiler hiện hữu.
- Review checks toàn bộ source leaf (hoặc raw block), mọi ô/trang/chú thích và
  title/heading/paragraph/table cell/unknown trong draft. Nguồn là snapshot đã
  dùng, không lấy latest OCR hoặc text review mới ghép vào lượt cũ.
- Server đòi mỗi ID đúng một lần, kiểm refs hai chiều; raw giữ khi schema/coverage
  sai. Quotes lấy từ server, model chỉ trả ID/trạng thái/lý do/gợi ý.
- Lưu report JSON+Markdown riêng với source/draft excerpts và metadata. Verdict
  server needs_attention/no_issues_detected, không tỷ lệ chính xác hoặc approved.
- Durable request trước quota commit, idempotency, expiry/fence, quyền/model/nguồn
  kiểm sau HTTP, không retry hoặc fallback; usage unknown giữ reservation.
- `0012_compiler_review` thêm2bảng riêng, downgrade chặn bảo toàn evidence; cập
  nhật route, ownership, migration imports và fixture/test ORM.

## Kiểm chứng

Cwd `D:/DuAnPhanMem/qnu-ai-platform/backendV1`. Wrapper ignored
`storage/context652/run_checks.py` dùng infra credential từ cấu hình hiện có
trong bộ nhớ, chạy harness tạo DB loopback mới, model/OCR giả lập. Không copy
row/key từ DB ứng dụng. Lệnh trong wrapper giữ log/XML/receipt cùng thư mục.

| Lượt | Kết quả |
|---|---|
| Baseline API `tests/integration/test_compiler_review_652.py -q` | 1FAIL404,8,21s/exit1 |
| Smoke API+ORM | 2PASS,7,76s/exit0 |
| Focused đầu review+ORM | 22PASS/1FAIL,103,16s/exit1; test kỳ vọng502 nhưng adapter truncated đúng hợp đồng422 |
| Focused cuối review+ORM+downgrade | 24PASS,102,53s/exit0; test kiểm chính xác mã theo mode, không đổi adapter |
| Extra3 | 2PASS/1FAIL,17,81s/exit1; test thêm thiếu importAPI, chưa lỗi runtime |
| Preferred reviewer sau thêm import | 1PASS/24deselected,8,07s/exit0 |
| Full v1, đủ4nhóm DB riêng | **460PASS/0FAIL/0ERROR/0SKIP**,25ca mới/0ca mất so với435ca651; tất cảexit0;383,56s wall |

Lệnh full là `storage/context652/full.py`: chọn mọi test file ở cả47tệp; chia
integration theo file vào3DB riêng, unit+migrations+contract+invariants vàoDB
thứ4. Không deselect/skip. Union4XML không trùng và chứa đủ435nodeID cũ. Tổng
thời gian case1019,24s, không phải thời gian wall. Đây là toàn bộ suite qua4nhóm,
không phải một process full. Không có hang hoặc lỗi ở4nhóm cuối.

Ruff/format16file PASS; mã thay đổi/new UTF-8 không BOM/LF. OpenAPI75path/101op,
70path cũ giữ nguyên contract.475file legacy khớp baseline đầu phiên; Compiler
service/execution/drafting cũ giữ.10tên DBtest kiểm lại0còn,0v1vector quan sát;
sentinel/version legacy giữ. Không reset hoặc xóa DB/collection dùng chung.
Chi tiết exactIDs/counts/parts tại `backendV1/storage/context652/test-summary.json`,
scope/hash/OpenAPI tại `scope-verification.json`, cleanup tại
`cleanup-verification.json`; đây là artifacts ignored, không chứa corpus thật.

25 ca review mới bao phủ hai hướng, excerpts/đúng revision/hash, bảng/0/blank/
header/năm/note, không đổi draft, model reviewer riêng, no_issues không approve,
coverage thiếu/trùng/foreign/schema/truncated/HTTPerror, role/scope/key, queued
Compiler/quota, storage fail/raw, duplicate giữa quota commit, quyền/provider/
revision/expiry giữa model, timeout unknown/reservation và blob checksum.
Fixture phát biểu omitted/contradicted là mô phỏng contract, không phải gold hoặc
bằng chứng model thật nhận ra lỗi. Chưa quality/live acceptance.

## Giới hạn

- Chỉ có report; người dùng muốn sửa Compiler phải tạo một phiên bản mới theo
  luồng được thiết kế tiếp. Không tự sửa bản đã duyệt/phục vụ.
- Review chủ động qua API, một request đồng bộ; chưa auto-call từ worker Compiler,
  ARQ review, multi-pass/chunk/batch, resume hoặc background reconcile.
- Text hậu OCR đã sửa vẫn chưa nối Compiler; giữ nguồn cũ theo đúng snapshot.
- No issues là nhận xét LLM, không bảo đảm đủ ngữ nghĩa; source OCR đã mất chữ
  không thể phục hồi chỉ bằng review text. Có thể phát hiện trùng một vấn đề ở2hướng.
- Báo cáo cũ khi nguồn revision mới bị chặn đọc như current; metadata/raw vẫn giữ
  theo quyền. Blob dở có thể mồ côi; chưa GC.
- Hai cảnh báo Starlette/AnyIO và rủi ro shutdown Proactor từ648/651 không sửa ở
  phiên này. Full chia nhóm đầy đủ không che lỗi run trước hoặc bỏ ca.

[API](../../../backendV1/docs/compiler-review.md) ·
[Quy trình28](../../quy_trinh/28_review_ngu_nghia_compiler_backendv1.md).
