# Bản vá context547 — phiên548

Phạm vi: vòng đời unresolved/review/policy/snapshot, scope nhiều năm, budget
nhất quán, deadline API/runner, atomic multi-packet và dossier có thể đóng gói.
Không đổi parser, Markdown Standard, retrieval, model defaults hoặc publication policy.

## Audit và phương pháp

1. `stage_semantic_annotations` chỉ đếm annotation, preview chỉ hiện proposed;
   `apply_reviewed_semantics` chưa chặn unresolved; `record_decision` dùng apply
   guard kể cả reject. Tách envelope validation khỏi application guard; context
   contract có version, stable IDs theo nguồn/đích, quyết định do server kiểm.
2. Scope nhiều năm bị reject và prompt ép span ngắn. Giữ full canonical unit,
   phân loại cần scope confirmation; không xem year overlap là chứng minh ngữ nghĩa.
3. Packet split/expand dùng hai bộ đếm. Dùng union IDs thực trên public payload
   cho table/header/full row/prose, directory chỉ tính bytes; validator chung.
4. API120s/runner125s khác nhau, timeout thành proposal invalid. Dùng một policy
   finite run/call deadline; provider errors giữ nguyên; check cancellation/deadline
   trước stage và chỉ stage trên bản copy rồi mới thay envelope.
5. Test later-packet hiện sai ngay response đầu. Regression phải thực sự bind
   packet đầu, fail packet2, không stage; thêm deadline/cancel và publication guard.
6. Snapshot v1 recipe giữ nguyên, snapshot mới version semantic hash ràng buộc
   context/issues/checked decisions. Replay quyết định không gọi model. Reject
   không thay active pointer nhưng issue còn mở phải sống qua rebuild.

## An toàn

READ ONLY xác minh DB127.0.0.1:5432, MinIO:9000, Qdrant:6333. DB test mới
`qnu_test_context548_ac0b8df43d40` với nonce ownership;49tables tạo chỉ ở đó.
Child ENVIRONMENT=test, auto migrate/seed false, StorageDriver local ở runtime
riêng, data services trỏ127.0.0.1:1. ModelOps cấu hình/keys mã hóa copy READ ONLY
sang testDB; không log secrets. Không chạy migration trên appDB. Cleanup sau export
dossier phải kiểm exact name/comment/absolute path và xác nhận không còn tồn tại.

Baseline hoàn chỉnh24FAIL/2266PASS/17skip, gồm6test đỏ mới và18lỗi nền;
code app baseline được pin vào copy có hash trước khi sửa caller. Historical547
không phải kết quả hiện tại. Lượt đầu bị ngắt chỉ là kết quả dở dang.
Chỉ đọc/đối chiếu prompt được user giao; không coi code mẫu là patch production.
