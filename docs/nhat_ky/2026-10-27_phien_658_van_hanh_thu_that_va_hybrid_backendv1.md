# Phiên658 — Vận hành, thử PDF thật và hybrid retrieval backendV1

## Yêu cầu và quyền đã xác nhận

User yêu cầu triển khai mục4–6: vận hành/job/backup/retention, chạy tài liệu thật
toàn luồng và hybrid/rerank/evaluation. User đã xác nhận gửi query/candidate tới
server AI được chỉ định, rồi cho phép PDF hai trang có sẵn đi qua Nemotron/Qwen/
BGE, giữ kết quả riêng và dọn DB/chỉ mục thử. Chỉ backendV1; UI làm sau.

Các phiên655–657 đã thuộc thay đổi frontend/SSO đồng thời, nên dùng nhật ký658. Artifact
riêng và test IDs vẫn mang nhãn context655. Không sửa hai file SSO thay đổi đồng
thời; giữ các thay đổi chưa commit, không reset/commit/push Git.

## Thay đổi và phương pháp

- API operations lấy job/progress/usage thực từ ledger hiện có, không tạo % hay
  cost giả. Preview/acceptance ghim actor/state/hash/expiry, outbox commit trước
  queue I/O; chỉ giao lại queued/hết lease, worker giữ checkpoint/quyền.
- Evidence backup MVCC + object SHA/inventory/readback; loại bảng credential,
  giữ nguồn/raw vô thời hạn; chỉ xóa backup hết hạn có preview/approval/audit.
  Đây chưa phải full DR/restore database hoặc Qdrant.
- FTS Unicode + dense/RRF, rerank qua ModelOps động, strict indices/score, quota,
  kiểm quyền/nguồn/config trước và sau HTTP. Không retry/fallback ngầm. Mode
  mới ở search/answer; assistant/conversation vẫn mặc định dense.
- Evaluator pin snapshot/gold/scope, cùng ứng viên B/C, giữ errors và nhãn draft;
  không gán answer correctness/groundedness hoặc approval giả.
- Lượt thật phát hiện model sai schema/coverage/refs. Thêm structured_output
  tường minh cho Compiler/review; review keyed theo ID và server vẫn kiểm đủ.
  Prompt dùng đầy đủ units + metadata tài liệu, bỏ bản sao văn bản lặp, không
  cắt source units. Snapshot/raw vẫn đầy đủ, giữ JSON/MD nhất quán.

File chính: `backendV1/qnu/domains/operations/`, `domains/evaluation/`,
`domains/knowledge/index/hybrid.py`, Compiler/review/answer và ModelOps adapter,
ports/wiring/worker settings; migration0014 và test có nhãn655. OpenAPI và các
docs operations/hybrid/compiler/port matrix được đồng bộ. Chi tiết file và
nghiệm thu tại [báo cáo656](../bao_cao/context658/REVIEW.md).

## Kiểm chứng thực chạy

Cwd `backendV1`; Python venv3.12, PostgreSQL/Redis/Qdrant loopback; harness có
guard chặn model ngoài cho regression. Lượt live dùng đúng PDF/server được phép.

| Lệnh/nhóm | Kết quả |
|---|---|
| `storage/context655/run_checks.py baseline …` | 4FAIL trước triển khai |
| Operations/migration; hybrid; evaluation | 5PASS;7PASS;6PASS |
| Hardening; guard/compatibility | 28PASS;48PASS |
| Backup text regression trước/sau sửa scope | 1FAIL →5PASS |
| Full đầu bị ngắt | Không nghiệm thu; một invariant placeholder lỗi được đổi sang kiểm upstream lỗi thật |
| Full sau ngắt | 535PASS,61file; có thêm thay đổi tiếp sau |
| `storage/context655/final_full.py` | 539PASS/1FAIL metadata text-version, exact ID trong báo cáo |
| `storage/context655/recheck_partition.py` | 58PASS, chạy lại trọn partition2 sau sửa code, giữ assertion |
| Hợp5 nhóm đủ toàn bộ node IDs | 540PASS/0FAIL/0SKIP;48mới của batch+2SSO đồng thời;0mất so490 |
| Regression sau các sửa nhỏ | 47PASS,42PASS,39PASS,36PASS ở các lượt riêng |
| `storage/context655/audit.py` | Ruff/format56file PASS; UTF-8/LF/OpenAPI92path119op;79path cũ giữ |
| Seal legacy đầu batch | 475/475 khớp byte; không phủ nhận drift lịch sử654 |

Full cuối hợp5partition có DB riêng,61file. Có hai cảnh báo deprecation từ
Starlette/TestClient/AnyIO; không sửa ngoài phạm vi. [Receipt công khai](../bao_cao/context658/verification.json)
ghi từng nhóm, rerun, trạng thái cleanup và giới hạn. Không báo PASS cho các lượt
FAIL/bị ngắt hoặc dùng test mock làm bằng chứng model thật.

## Lượt thật và bằng chứng chất lượng

PDF hai trang → OCR4,875s → saved text version → Compiler19,266s → review39,250s
→ publication riêng → index1,375s → answer3nguồn/4.590chat token → backup0,812s,
verify=true. Đã dọn DB và một collection vector thử. API qua TestClient và
worker entry thật; transport ARQ kiểm riêng. Snapshot/output riêng không vào Git.

Review kiểm21source/20draft units,6findings `needs_attention`; chưa human-check.
Ba câu literal lookup proxy cùng snapshot/candidates có dense Recall@3=1,0;
hybrid/rerank=0,833; Hit/MRR đều1,0. Không có bằng chứng tăng chất lượng, giữ dense.
Nhãn draft, chưa holdout/câu độc lập/answer quality/performance load acceptance.

Các lỗi live trước vẫn giữ riêng; mỗi chẩn đoán dùng run/DB mới, không reset hay
resend job uncertain. Một lượt bị ngắt và một lượt output truncated. Backup
scope `ocr-text` được sửa sau regression đỏ. Metadata phiên bản nguồn được phục
hồi sau full test phát hiện thiếu; không sửa test để che mất provenance.

## Cleanup và bàn giao

Đã kiểm 37 tên DB do các receipt của task xác định;0DB còn.
Bốn DB bị ngắt kiểm sentinel/version rồi dọn đúng tên. Quan sát cuối có
0 collection vector v1. Không xóa wildcard, không đụng DB/vector phục vụ.
Chỉ giữ artifact riêng theo yêu cầu; không đưa credential/prompt/corpus vào docs.

Chưa migrate/config/restart/deploy dịch vụ đang phục vụ, reindex corpus hoặc UI;
chưa full DR, GC orphan/generation, GIN, streaming hay assistant retrieval settings.
Review chưa là publish gate; kết quả model vẫn cần người dùng đối chiếu.

Quy trình: [30 — Vận hành và hybrid](../quy_trinh/30_van_hanh_va_hybrid_backendv1.md).
