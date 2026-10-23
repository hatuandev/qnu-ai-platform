# Phiên606 — Rõ nghĩa unknown và kiểm chứng compiler bằng Qwen

Ngày23/10/2026. Người dùng cho phép tiếp tục kiểm direction, coverage và ba DOCX trước đợt5; sau đó đề nghị đổi tên unknown để model không nhầm ý nghĩa. Giữ Qwen chính, không gọi Luna, không đổi nguồn/model/reindex/publish/commit/push.

Context606 đã đổi nhãn assertion trên wire thành source_unspecified/null, tách verdict unresolved và giữ unknown/null đã lưu. Kiểm chiều quan hệ PASS và đối soát ba coverage dispute; thêm source limitation guide, local graph guard và cap4primary để chừa đầu ra. Focused169/Ruff10/31test mới PASS; full3551PASS/18FAIL baseline/17SKIP,+23subtestPASS, exact ID/cause giữ. Toàn90usage Qwen,0Luna/fallback. Ba full compiler trước alias FAIL; probe cuối extraction đúng alias nhưng temporal review/empty-draft schema vẫn FAIL, chưa APPROVED/compiler bundle. Source/model/config/vector2943/0retrievable giữ,2DB test dọn/Storage giữ policy. Không benchmark64/reindex/publish/restart/commit/push.

## Phương pháp và thay đổi

Đã đọc AGENTS/memory/diff, dùng các skill Clean Code, backend, ingestion và ModelOps trong phạm vi tương ứng. Không tạo subagent. Đọc raw DOCX và proof catalog trước kết luận, không dựa nguyên báo cáo604. Sáu file app: compilation_runtime_schemas.py, compilation_schemas.py và services/compilation_coverage.py, compilation_engine.py, compilation_modelops.py, compilation_transport.py. Không sửa parser hoặc RAG serving.

Chỉ đổi value_state tại ranh giới model, không tìm/thay unknown trong dữ liệu gốc. Source unspecified có bằng chứng vẫn có thể supported; unresolved là thiếu bằng chứng kiểm chứng nhận định. Schema/state/value/proof guards giữ nguyên, local graph được kiểm sớm. Cache version/hash đổi theo hợp đồng; không dùng bundle cũ như kết quả mới.

31test mới606 kiểm local graph, scalar/null, output packing giữ proof/dependency, compile/reload giới hạn nguồn, unresolved không bị override, cache và adapter alias/empty review. Test fixture engine/lifecycle thích ứng packet thực, vẫn kiểm exactly-once proof coverage và reuse/revocation/idempotency.

## Bằng chứng và giới hạn

- [Triển khai](../bao_cao/context606/IMPLEMENTATION_REPORT.md).
- [Kiểm chứng, lệnh, môi trường và các lần FAIL](../bao_cao/context606/VALIDATION_REPORT.md).
- [Exact test IDs/cause](../bao_cao/context606/TEST_ID_COMPARISON.md).
- [Ba dispute và chiều quan hệ](../bao_cao/context606/RECONCILIATION.md).

Regression dùng DB/Storage riêng, network guard; đã kiểm kết nối DB/MinIO/Qdrant trước chạy. Baseline18FAIL giữ nguyên ID/cause; full cuối vẫn FAIL. Lượt full trung gian và interrupted giữ riêng. Mock regression không phải upstream E2E.

Real compiler dùng canonical602 của ba DOCX2024–2026,381noncontainerproofs; không fresh parse/full QG. API create/read thật qua ASGI trên fixture test, không browser/published chatbot E2E. Chưa có bundle606 hoàn thành. Hướng dẫn mới/alias không đủ sửa hết việc Qwen không tuân thủ schema và review thời gian; không hạ gate, không tự điền supported hoặc resend uncertain intent. Đã dừng whole-build lặp sau probe hẹp còn thất bại.

Hai DB test đã dọn bằng exact name+nonce ownership; Storage giữ vì policy bảo vệ từ trước, không tìm cách bypass. Read-only seals/sourcebytes/vector payload giữ. ModelOps usage90Qwen success chỉ là tầng inference, không semantic PASS;255072input/24372outputtokens. Token Saver/32K chưa có đối chứng để quy nguyên nhân; không thay kết quả Luna lịch sử.

## Tiếp tục

Chưa chuyển đợt5/serving. Cần xử lý output contract compiler (hiện schema trong prompt và validation sau inference) hoặc review rỗng thành yêu cầu coverage phù hợp, giữ proof/null/missed-evidence và budget. Phần đó chưa triển khai trong606. P10/benchmark64/FE ngoài phạm vi lượt này.
