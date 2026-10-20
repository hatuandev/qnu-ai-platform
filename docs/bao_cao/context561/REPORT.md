# Context561 — Dọn kho tuyển sinh và kiểm thử đến xuất bản

Hoàn tất ngày 2026-10-20 (Asia/Bangkok); công việc bắt đầu ngày 2026-10-19.

## Kết quả

**Luồng nạp tài liệu thật và xuất bản: PASS.** Kho `col_admissions` hiện chỉ phục vụ DOCX vừa nạp lại. Regression theo ID: không còn lỗi mới. Full backend suite vẫn **FAIL**: 2494 PASS, 18 FAIL, 17 SKIP, 23 subtests PASS; exit 1.

Người dùng đã xác nhận **dọn toàn bộ col_admissions** và kiểm thử đến xuất bản. Quyền này thay thế giới hạn chưa xuất bản của phiên trước, không mở rộng sang Kho tài liệu gốc hoặc collection khác. Không commit/push/deploy; phiên này không restart dịch vụ.

## Dọn kho

- Bảy nguồn còn nội dung đã được pause và purge qua API, worker thực thi thật, bảy job completed. Xóa 15 source revisions cũ, chunks/facts và vector dẫn xuất.
- 318 điểm vector cũ → 0 trước khi nạp lại. Không xóa collection Qdrant hoặc cấu hình ModelOps/collection.
- Giữ 22 binding rỗng và các index `pruned` để bảo toàn lịch sử xuất bản. Chúng không hiện như nguồn đang dùng và không lọt snapshot phục vụ.
- Dọn thêm 33 sidecar cũ, 22390544 bytes. Kiểm tra trước từng đợt: prefix đúng binding cũ, không revision/Repository nào tham chiếu, ETag/size chưa đổi, không job đang chạy; xóa qua StorageDriver. Sau cùng còn 0 snapshot object dưới các binding cũ.
- Toàn bộ bản ghi Repository và collection khác khớp seal trước/sau; bytes DOCX local và trong Kho tài liệu giữ nguyên.

## Luồng kiểm thử thật

| Bước | Bằng chứng | Kết quả |
|---|---|---|
| Tải DOCX | Multipart `/documents/intake`, HTTP 202; hash nguồn khớp | PASS, deduplicated=true |
| Import mới | Binding `bnd_fa71a57c9cf1`, revision mới; không tái dùng binding đã xóa | PASS |
| Kiểm tra hình | Revision đầu bị chặn đúng `figure_content_unverified`; dùng lại xác nhận Hình 1 của người dùng sau kiểm tra source/image/transcription hash | PASS |
| Markdown/JSON | 233 khối, 10 bảng; toàn bộ body, raw cells, spans và hierarchy khớp chuẩn đã đối soát; hash pair/download khớp | PASS |
| Readiness | READY_WITH_LIMITATIONS; 0 blocker; unknown không tạo numeric fact; không áp proposal ngữ nghĩa chưa duyệt | PASS |
| Vector | Job `job_e8b97258204c`; 262 chunks / 368 facts; parity thật | PASS |
| Facts trước publish | So toàn bộ giá trị, confidence, raw provenance và identity; validator nguyên vẹn | PASS |
| Xuất bản | `publish-selected` HTTP 200; index `idx_rev_967891af9d5d`, một activation audit | PASS |
| Sau publish | 262/262 điểm `is_retrievable=true`, status ready; snapshot chỉ trỏ một binding/index mới; không điểm nguồn cũ | PASS |
| Truy xuất phục vụ | AM-0007 và AM-0070 đều trả 5 kết quả từ nguồn/index mới; snapshot cũ bị từ chối; không gọi LLM/embedding thêm | PASS |
| Guard mới nhất | Đọc lại nguồn đang xuất bản bằng matcher native mới, không sửa immutable MD/JSON hoặc reindex | PASS |

Nguồn đang phục vụ: revision `ks_rev_ca1e7f16d9e0`. [Mở trong ứng dụng](http://localhost:3000/knowledge/col_admissions/sources/bnd_fa71a57c9cf1?revision=ks_rev_ca1e7f16d9e0&tab=content).

Intake, cleanup, vector queue và publication được gọi qua HTTP thật. Import/reparse dùng entrypoint worker chính thức, chạy inline với lease và mã hiện tại, DB/Storage thật; không giả lập thành browser hoặc broker E2E. Vector chạy qua ARQ/worker thật và provider embedding cấu hình sẵn. Actor là actor development được server xác thực, không phải kiểm chứng SSO production. Không gọi chat LLM để đánh giá câu trả lời trong ca này.

## Sửa lỗi và bảo toàn Quality Gate

1. Identity facts phải được tính sau khi hoàn tất provenance của từng hàng. Lỗi cũ có 105 entity_key sai giữa projection/ORM trong 368 facts. Policy mới `final-cell-provenance/v1` áp vào nguồn bóc tách mới; legacy không được viết lại âm thầm. Không bỏ entity_key khỏi so sánh hoặc hạ parity gate.
2. Full regression phát hiện nhãn header chưa rõ bị xóa khi chứng minh nguyên văn. Nay giữ nhãn với trạng thái `literal_only`, vai trò cột vẫn unknown, không numeric facts. Chứng minh nguyên văn không trở thành chứng minh header.
3. Hai bảng giống nội dung nhưng khác header không được phân biệt bằng chính role đang cần xác minh. Matcher yêu cầu duy nhất theo các ô nguồn trước khi kiểm tra header; thiếu association thì không cấp chứng nhận, vẫn giữ blocker.

Phiên bản extraction mới nhất: `layout-v21-native-role-safety`. Nguồn thật của ca này được tạo bằng v20 và đã kiểm tra lại đạt với guard mới; không thay metadata/hash lịch sử chỉ để đổi tên phiên bản. Không sửa canonical pair đang phục vụ sau publication.

## Kiểm thử và giới hạn

- TDD identity: lượt đầu 4 FAIL/1 PASS, exit 1; ba failure phản ánh contract thật, một assertion ban đầu đặt mã định danh sai vào entity_text đã được sửa để kiểm raw cell. Lượt cuối identity/serving/publish/automatic: 50 PASS, exit 0.
- Sau sửa association/nhãn: focused 87 PASS, exit 0; gồm regression header/cell, native layout, automatic ingestion, serving, identity, selected publication và figure review.
- Scoped Ruff đạt. Full đầu 21 FAIL cho thấy focused không đủ; đã xử lý ba regression và chạy full lại trên DB test mới. Đối chiếu từng ID và nguyên nhân tại [REGRESSION_IDS.md](REGRESSION_IDS.md); không chỉ so tổng số.
- Test DB local riêng, Storage tạm riêng; MinIO/Qdrant/Redis của test harness trỏ cổng không phục vụ để tránh ghi nhầm. Không migrate production hoặc dùng DB ứng dụng cho pytest. Các thao tác dữ liệu thật chỉ thuộc phạm vi collection người dùng đã duyệt.
- Source limitations còn giữ nguyên. Một footnote chưa xác định trang preview nhưng có nguyên văn và anchor Word; không tự đoán trang. Hàng/cột chưa đủ vai trò chỉ được dùng như mô tả, không tạo số liệu hoặc quan hệ chắc chắn. Xác nhận hình không đồng nghĩa duyệt 12 assertion/proposal ngữ nghĩa cũ.
- FE lint/build và browser E2E không chạy trong phiên này vì không sửa frontend. Không coi API/worker thật là đã kiểm thử toàn bộ thao tác browser hoặc câu trả lời RAG.

Lệnh full cuối, chạy từ root repository (runner đặt cwd pytest về `backend`):

```text
backend/.venv/Scripts/python.exe backend/scripts/context_patch_validation.py run --state-file backend/storage/context561/isolation-final.json --audit-file backend/storage/context561/safety.json --evidence-dir backend/storage/context561/tests --label full-after-layout
```

Các lệnh thực thi live: `cleanup_collection.py`, `reimport.py`, `validate_and_vector.py`, `publish.py`, `storage_audit.py`, `remove_orphan_snapshots.py`, `final_audit.py`, `retrieval_smoke.py` trong evidence riêng Context561, dùng cùng Python trên. Intents/receipts chống gửi lại mù khi chưa chắc kết quả. Không phải endpoint mới hoặc code production nhúng dữ liệu test.

## Dọn môi trường test

Đã xác minh database test của Context560 và hai lượt Context561 được drop theo nonce sở hữu; trạng thái cuối ghi trong các file isolation và cleanup. Các báo cáo/checkpoint riêng được giữ để đối soát.

**Kiểm duyệt tự động từ chối xóa đệ quy runtime test, lý do `blocked by policy`.** Không đổi shell, dùng cơ chế khác hoặc tắt bảo vệ để vượt chặn. Thư mục runtime test còn giữ lại; đây không phải snapshot/nguồn của kho đang phục vụ. Chi tiết và số lượng tại evidence riêng `backend/storage/context561/`.

## Evidence và phạm vi mã

Evidence riêng: `backend/storage/context561/`: preflight, cleanup intent/receipts, manifest Storage, upload/import receipts, canonical pair, pre-vector/pre-publish/post-publish checks, Qdrant parity, final audit và JUnit. Không đưa corpus hoặc credential vào Git.

Phần app/test hiện sửa: `docx_layout_fidelity.py`, `source_extraction.py`, `test_docx_layout_fidelity.py`; bản sửa identity ở `qnu_projection.py` và test riêng đã có trong checkout khi tiếp tục. Không stage/reset thay đổi của người dùng.
