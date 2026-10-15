# Phiên 449 — Tham khảo dữ liệu năm cũ khi chưa đủ căn cứ cho năm được hỏi

## Mục tiêu và quyết định đã được người dùng duyệt

Người dùng cho phép câu hỏi năm 2026 được trả lời một phần bằng thông tin năm 2025 đúng chủ đề, nếu ghi rõ năm của thông tin và chưa có căn cứ xác nhận cho năm 2026. Triển khai tổng quát theo năm được hỏi/năm trong dữ liệu, không hardcode năm, tên ngành, câu hỏi hoặc model.

## Thay đổi

| Tệp | Nội dung |
| --- | --- |
| `backend/app/modules/rag/evidence_historical.py` | Nhánh tham khảo lịch sử riêng: tìm năm trước gần nhất có ứng viên liên quan, tra cứu lại cùng snapshot và cùng tuple ngữ nghĩa, kiểm chứng rồi ghép phản hồi có nhãn năm. |
| `backend/app/core/evidence_policy.py` | `historical_reference_enabled=True` mặc định trong chính sách evidence; có thể tắt bằng cấu hình, không ghi DB trong phiên này. |
| `backend/app/modules/rag/evidence_schemas.py` | Planner có `historical_reference_allowed` để giữ yêu cầu người dùng cấm tham khảo khác năm. |
| `backend/app/modules/rag/evidence_model.py` | Chỉ dẫn planner/proposal/verifier phân biệt năm hỏi và năm của lượt tham khảo. Giữ nguyên các sửa đổi chưa commit từ phiên trước. |
| `backend/app/modules/rag/evidence_indexed_audit.py` | Audit độc lập cũng đối chiếu riêng năm tham khảo, không đòi chứng minh năm gốc cho phần thông tin lịch sử. |
| `backend/app/modules/rag/evidence_pipeline.py` | Thêm nhánh tham khảo sau trả lời chính, trong timeout chung; latency tính cả nhánh bổ sung. Không đưa DAG trở lại chat. |
| `backend/app/modules/rag/evidence_validation.py` | Chặn mệnh đề có năm nội dung cũ dưới năm hỏi mới khi metadata chưa xác minh; guard hỗ trợ quyết định tham khảo có nhãn, kiểm tra năm/chứng cứ/status để không nâng thành supported. Giữ tương thích caller chỉ kiểm refs, không có text. |
| `backend/tests/test_historical_reference_449.py` | Test-first và các kiểm thử dương/âm về năm, provenance, nhãn, dữ liệu rỗng, DB/model lỗi, xung đột và tính đầy đủ. |
| `docs/quy_trinh/03_hybrid_rag_truy_xuat.md` | Đồng bộ quy trình tham khảo khác năm. |

## Thuật toán và hợp đồng

1. Chạy luồng evidence bình thường cho năm yêu cầu trước, bao gồm corrective retrieval hiện có.
2. Chỉ thử tham khảo khi quyết định chính là missing/partial và chưa có claim được chấp nhận. Không thay thế supported, không che conflict/clarify, không đè các phần đã trả lời có căn cứ của năm mới.
3. Chỉ áp dụng cho một năm dữ liệu; không tự thay các năm xuất bản, năm sự kiện hoặc câu so sánh nhiều năm. Nếu người dùng cấm tham khảo khác năm thì bỏ qua.
4. Xếp hạng ứng viên bằng BM25 hiện có trên kho published đã pin và các hàng reviewed; ưu tiên năm dữ liệu verified. Nếu metadata chưa verified, năm trong nội dung hoặc heading thực cùng source chỉ là gợi ý để tìm, không tự chứng nhận năm. Không dùng năm từ filename, title metadata hoặc ngày ban hành.
5. Chọn một năm nhỏ hơn năm yêu cầu, gần nhất trong các ứng viên. Tra cứu và kiểm chứng riêng theo năm đó, giữ thực thể/thuộc tính/trường/phương thức/đợt/sự kiện và toàn bộ cấu hình provider/model/reranker. Chỉ một lượt tham khảo; không tăng quota hoặc thay deadline chung.
6. Cần claims đã kiểm chứng đúng chủ đề, đủ điều kiện; cả verifier và audit phải chấp nhận tính đầy đủ cho lượt tham khảo. Mỗi claim phải có chứng cứ năm của chính nó (metadata data-year verified hoặc quote scope cùng source); không trộn năm hoặc mượn heading của source khác.
7. Phản hồi luôn có `answer_decision.status=partial`, `reason=HISTORICAL_REFERENCE_ONLY`, `requested.years` giữ năm gốc và `historical_reference={requested_year, reference_year}`. Bằng chứng/trích dẫn/span/hash không bị đổi năm. `status` API vẫn `insufficient_context` vì chưa đủ căn cứ cho năm được hỏi.
8. Hiển thị rõ: chưa tìm thấy căn cứ **đã kiểm chứng đủ rõ trong kho đang dùng**, thông tin năm cũ chỉ để tham khảo và không xác nhận áp dụng cho năm mới. Không khẳng định Trường chưa công bố thông tin hay cả kho không có dữ liệu.
9. Lỗi DB/ModelOps/timeout vẫn trả lỗi thật; không kích hoạt tham khảo để che lỗi dịch vụ. Guard từ chối label bị bỏ, reference year tương lai, nâng status thành supported hoặc sửa metadata không khớp proof.

Các skill RAG/Backend/Chatbot/Clean Code được dùng để giữ shared evidence path, async/RFC7807, trích dẫn và kiểm thử test-first. Không sửa parser tài liệu, không tạo luật từ vựng theo ngành/câu hỏi. Không chỉnh các lỗi audit/formula/locator khác đã ghi phiên 446.

## Kiểm thử

- Test-first: 2 ca thất bại đúng nguyên nhân trước sửa (missing không có tham khảo; claim explicit 2025 vẫn pass với yêu cầu 2026 khi metadata unknown).
- Focus cuối: **159 passed**, gồm các suite historical reference, knowledge units, evidence claims/priorities/quality/completeness và temporal fact contract.
- Ruff toàn Backend: **đạt**, có cảnh báo ACL đọc thư mục pytest cũ, không sửa quyền hay xóa chúng.
- Full đầu: 1305 passed / 12 failed / 15 skipped. Một fail mới là caller chỉ có refs không có text; đã sửa bằng `claim.get("text")`, kiểm thử knowledge units và historical chạy đạt. 11 fail khác trùng baseline.
- Full cuối: **1308 passed / 11 failed / 15 skipped / 0 errors**, 171,86 giây, XML `backend/storage/pytest449_release.xml`. Đối chiếu bằng tên testcase với `pytest443_release.xml`: `FailureDifferences=[]`; không fail mới. **32/32 ca historical reference đạt**. Sau chỉ dẫn audit cuối, focus159 và Ruff file liên quan chạy lại đạt.
- 11 lỗi nền: 2 export consulting, 6 API publishing/GC/decommission/canary, reconciliation discrepancies, auth role `admin`/`AI.Admin`, universal admissions export. Không sửa lan các chức năng này. Lượt full vẫn có log đóng kết nối asyncpg/Windows không liên quan nhánh historical.
- Test hợp đồng dùng đầu ra model kiểm soát được và kiểm chứng span/temporal/audit/guard thật; không lấy đây làm đánh giá chất lượng model trực tiếp. Chưa gọi 9router hoặc chạy lại 20/82 câu thật; không tuyên bố accuracy/TM-08.
- Không thay Frontend, không chạy Vite build.

## Phạm vi vận hành và việc còn lại

Không reset DB, sửa nguồn Word, upload, duyệt, nạp lại vector, publish, đổi model/provider/reranker/quota hay restart dịch vụ. Cơ chế mới nằm trong shared evidence path đang dùng cho chatbot RAG. Luồng legacy chưa bật evidence policy không được thay đổi trong phiên này.

Sau khi Backend nhận code mới, nên kiểm tra vài câu đủ nguồn năm yêu cầu, chỉ có nguồn năm trước và không có nguồn nào, rồi mới chạy lại bộ câu hỏi lớn. Các sai lệch nội dung cẩm nang ở phiên 448 và lỗi bóc tách bảng/heading ở phiên 447 vẫn là công việc riêng.
