# Phiên 466 - Giai đoạn 1: chẩn đoán điểm sàn sau reset DB

Ngày 2026-10-15. User yêu cầu triển khai giai đoạn 1, sau đó báo đã reset DB/nạp lại.

## Mục tiêu và ranh giới

Đối soát Thông báo 121, hai câu Quản lý giáo dục/Sư phạm Toán học, trace luồng thật
và regression tái hiện. Không sửa runtime, đổi cấu hình/model, reindex hay publish.
Áp dụng hướng dẫn Clean Code/Backend/RAG/Ingestion và PDF visual verification.

## File thay đổi

- [Công cụ audit](../../backend/scripts/audit_rag_floor_stage1.py): inspect transaction READ ONLY,
  phân giải snapshot sau reset, binary checksum, render, optional trace service thật;
  wrapper quan sát không giả lập kết quả. --live ghi hội thoại/usage/key-health bình thường.
- [Test regression](../../backend/tests/test_rag_floor_stage1_466.py): 5 controls, 4 open strict xfails.
- [Fixture](../../backend/tests/fixtures/rag_floor_121_excerpt.md): trích canonical hai hàng,
  không thêm binary/PDF/ảnh vào test source, không dùng làm dữ liệu runtime.
- [Báo cáo đầy đủ](../kiem_thu/2026-10-15_rag_giai_doan_1_diem_san_121.md).
- Đồng bộ nhật ký/memory/WORK_LOG/snapshot. Không đổi tài liệu quy trình vì chưa đổi lifecycle/runtime.

## Kết quả

- Nguồn local khớp origin PDF SHA-256; xem trang 1/2/7/8: số 121, ngày 09/07/2026;
  QLGD 15/18/600/15, SP Toán 20/–/–/20; dấu – có chú giải trang 8.
- DB mới có 21 nguồn active, epoch2/fingerprint c61c923b10b4f8f1aa58. Nguồn điểm sàn
  bnd_e4b071bb147f / ks_rev_73ea05d14446 / idx_rev_a443d796d020,86chunks284facts.
- Đối soát trực tiếp Qdrant 86/86 point ID/revision/content hash đạt, không upsert.
- Hai hàng và header kế thừa trang2 đúng; chưa tái hiện mất header ở nguồn này.
- Native bỏ số/ngày trên ảnh; metadata null. Scope năm của ô null; điểm học bạ 18
  gán admission_method và điểm sàn gán cutoff_score. Không tự suy năm từ ngày ban hành.
- Reset để evidence_policy.enabled=false, execution_mode=rag: luồng legacy chứ không
  evidence QueryPlan/BM25/semantic audit/historical path đã khảo sát trước.
- Baseline genuine model ngoài sandbox: QLGD answered nhưng chỉ15, SPToán answered
  nhưng nói không có thông tin2026. Chưa đạt 2/2 yêu cầu, không phải 82-case accuracy.
- QLGD dense có hàng đúng hạng11 rồi rơi trước context; SPToán không có hàng ở topK.
  Facts lookup LIMIT5/10 trả dữ liệu khác/năm cũ, không có ô điểm sàn đích.
- Primary vLLM HTTP400 input>=3193 + output5000 > window8192; cả2 served Cloudflare.
  Không đổi max_tokens/model/capability để baseline đẹp. Has-evidence làm refusal bị answered.
- 2 lượt trong sandbox trước đó lỗi kết nối đã loại khỏi baseline; 4 hội thoại test tổng cộng.
- Fingerprints config/publication/targetsource+facts+chunks/metadata không đổi; không
  khẳng định toànDB read-only vì testing tạo log bình thường.

## Verification

- Red run `--runxfail`: 5 passed /4 failed đúng ba nhóm lỗi (classifier2/column1/refusal1).
- Focus units/temporal/table/source controls: **78 passed,4 xfailed,6,53s**.
  Strict xfail là lỗi còn mở, không phải fix đã pass; sửa sẽ XPASS để buộc xem lại marker.
- Ruff scoped/toàn Backend đạt (cảnh báo quyền đọc artifact cũ); UTF-8 6 tệp mới và
  scoped diff-check đạt. Hash runtime sau cùng khớp baseline. Full suite/FE build
  không chạy: phase chẩn đoán không runtime change.
- `uv run --no-sync ruff` ban đầu bị cache permission; dùng Python venv chạy Ruff/Pytest,
  không cài/cập nhật dependency.
- JSON/PNG/JUnit ở backend/storage là local artifacts, không stage/push.

## Bài học / tiếp theo

Kiểm tra execution mode và policy sau reset trước khi tối ưu nhánh không chạy.
Không quy thiếu ý chỉ cho context: hàng đúng còn chưa vào prompt. Giữ parser controls
đang đạt, xử lý metadata/typed scope, entity+metric candidate selection, window budget
và completeness/status theo kế hoạch được duyệt. Chưa bước sang giai đoạn 2.

Không thay app/models/keys, DB schema, nguồn/vector; không xóa docs/tai_lieu hay chạm Git index;
không commit/push/deploy/restart. Không chạy lại 20/82 câu.
