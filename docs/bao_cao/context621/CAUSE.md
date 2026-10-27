# Context621 — Vì sao chỉ tiêu2026=5.173 chưa vào bản compiler cuối

Ngày24/10/2026. Chỉ phân tích offline, không sửa ứng dụng, không gọi lại model hoặc toàn bộ tài liệu.

## Kết luận

**Dữ liệu không bị bóc thiếu; Luna đã trích đúng5.173 ở lượt sửa. Giá trị đúng không được nhận vì cùng gói sửa còn một assertionunknown sai. Cơ chế hiện tại từ chối cả gói rồi giữ bảnunknown ban đầu.**

Số liệu dưới đây là nội dung nguồn DOCX kiểm thử được cung cấp, không phải xác minh độc lập chỉ tiêu tuyển sinh thực tế của trường.

## Truy vết từ nguồn đến kết quả

| Bước | Bằng chứng đã kiểm tra | Kết quả |
|---|---|---|
| DOCX gốc2026 | Paragraph6, hashrawkhớp manifest602 | Ghi5.173 cập nhật theoThôngbáo1906 ngày31/05/2026, thay4.500 theoThôngbáo263 ngày12/02/2026 |
| Canonical Markdown | `proof_4520f268b355dafd5270c672` | Đoạn văn đầy đủ, khớp nguyên paragraphDOCX |
| Gói request59 | Cả đoạn trên được giữ trongevidence; spanliteral`5.173` có role`scalar` | Không mất source, không thiếu span ID, không bị enum chặn giá trị |
| Draft59 | Chọnstate`unknown`,value=null; limitation lấy từ`proof_f8d41b3b3d355a5358ddc45c` | Lấy câu “không tự động áp dụng cho mùa tuyển sinh khác” làm bằng chứng thiếu giá trị |
| Truth review60 | Verdictcontradicted | Reviewer chỉ rõ nguồn đã có5.173; giới hạn mùa tuyển sinh không chứng minh thiếu số liệu |
| Candidate correction62 | Model tạo hai assertion | Một assertionpresent/5.173/data2026 đúng; thêm một assertionunknown/null sai dựa vào câu phạm vi |
| Truth review63 | Assertion5.173=supported; assertionunknown=contradicted | Gói sửa khôngcomplete |
| Nhận bản sửa | `accepted = candidate.review.complete and not unchanged` | Cả gói bịrejected; active draft giữunknown ban đầu; candidateđúng chỉ còn trong ledger/chứng cứ |
| Synthesis66 | Assertionunknown cũ vẫn là đầu vào có hiệu lực | Reviewer tiếp tụccontradicted; không nghiệm thu |

Ở correction62, các trườngđơnvị/nhãn được copy từ spannguồn, nhưng không dùng việcliteralđúng để tự coi toàn candidate đã đạt. Chỉ tiêu mới5173 được reviewer hỗ trợ rõ ràng; nhận địnhunknown thêm vào vẫn sai.

## Nguyên nhân trực tiếp và khoảng hở thiết kế

**1. Nhầm hai nghĩa của “giới hạn nguồn”.**

“Thông tin chỉ áp dụng cho năm2026, không tự động áp dụng cho mùa khác” là **giới hạn phạm vi áp dụng**. Nó không có nghĩa “tài liệu không nêu chỉ tiêu2026”. Model dùng câu này làm`limitation` cho`source_unspecified`, trong khi cùng request có số5.173 rõ ràng.

**2. Menu span kiểm tra nguồn/vị trí/role cấu trúc, chưa phân loại ý nghĩa giới hạn.**

`compilation_span_menu.py` dùng cùng tập scalar-primary cho`scalar` và`limitation`. `compilation_transport.py` cũng dùng cùng`scalar_span` cho hai trường. `materialize_packet` kiểm span tồn tại, thuộc nguồn/primary đúng, có limitation nếuunknown, rồi chuyển alias`source_unspecified` thànhunknown. Các bước ấy không tự chứng minh câu limitation diễn đạt việc thiếu giá trị; phần kiểm tra ngữ nghĩa đặt ở truth review.

Đã tái hiện bằng hàm thuần: một proposalpresent/5.173 materialize được; một proposalunknown lấy câu giới hạn mùa khác cũng qua cấu trúc. Đây không phải nghĩa cả hai đều hợp lệ ngữ nghĩa. Blind review đã chặn proposalunknown đúng yêu cầu; không cần hạ Quality Gate.

**3. Repair hiện nhận hoặc loại toàn bộ candidate.**

`compilation_candidate_repair.py:47` đòi`candidate.review.complete`; dòng48 chọncandidate nếuđạt, ngược lại chọninitial. Lượt này`repeats_failed_assertion=false`: nguyên nhân loại không phải guard chống đổiID/verdict-shopping, mà là vẫn còn assertioncontradicted trong candidate. Vì candidate có cả tốt và xấu, giá trị5.173 đúng bị giữ ngoài bản có hiệu lực cùng với assertionxấu.

Đây là cơ chếfail-closed hiện hành, không phải server tự sửa5.173 thànhunknown. Cần sửa cách phân loại và cách tạo/nhận proposal sửa; không đơn giản bỏ điều kiệncomplete để nhận thêm fact.

## Những nguyên nhân đã loại trừ

- Không phải lỗi parserDOCX hoặc mất nội dung khi tạoMD: raw/canonical/request khớp chính xác.
- Không phải thiếu`span_id`5.173 hoặc role`scalar`: menu có và có thể materialize giá trị đúng.
- Không phải context hay output bị cắt: request59 có**9492input/634output**,finishstop; capacityprovider1050000. Số đếm request khớp usage đã lưu.
- Không phải model hoàn toàn không hiểu được5.173: correction62 đã đưa số đúng, reviewer63 xác nhận.
- Không phải riêng lỗi lưu`grounded_coverage_review_missing`: việc loại candidate2026 và giữunknown xảy ra trước bước lưu; hai vấn đề phải xử lý riêng.

Không có đủ bằng chứng để suy diễn chính xác quá trình suy nghĩ nội bộ khiến model chọn limitation sai ban đầu. Các log chứng minh lựa chọn đã xảy ra và đường xử lý sau đó; không cần gọi lại LLM để đoán nguyên nhân.

## Hướng sửa đề xuất, chưa triển khai

1. Phân biệt chứng cứ **thiếu giá trị**, **giới hạn phạm vi**, **điều kiện/ngoại lệ**, **mâu thuẫn**. Câu giới hạn mùa khác giữ trong scope/qualifier của factpresent; không tự làm giá trị năm2026 thànhunknown. Phân loại dựa vào chứng cứ nguồn và review, không từ điển gõ tay hoặc hardcode5173/2026.
2. Cho repair nhắm đúng assertion bị từ chối và có mappingthaythế rõ ràng. Một correction số liệu không nên phát sinh lại assertionunknown cùng chỉ số. Chỉ nhận phần sửa đã reviewđạt sau khi kiểm đủ coverage, nguồn/hash/scope và dependency; phầnchưađạt vẫn quarantine/unresolved cóaudit. Không âm thầm cắt assertionxấu rồi coi cả góiPASS.
3. Giữ riêng giá trị cập nhật5173 và giá trị trước4500 theo quan hệngày/thôngbáo được nguồn nêu; không chọn một số chỉ vì xuất hiện đầu tiên hoặc phù hợp câu hỏi.
4. Regression cần bao quát: giá trị rõ+phạmvihẹp; giá trị thật sựkhôngđượcnguồnnêu; cậpnhậtthaythếsốcũ; gói sửa có assertionđúng lẫnsai; repair không đổi năm/chủthể và không bỏ coverage.

## Kiểm chứng và phạm vi

Tám probe`Q621-01`–`Q621-08` đạt, exit0: hashDOCX, quote đầy đủ, scalar eligibility, limitation eligibility, materializationđúng/sai vềcấu trúc, candidate rejection và requestbudget. Đây là kiểm chứng chẩn đoán, không phải toàncompilerPASS.

Artifact`backend/storage/context621/validation.json` và`analysis-private.json`; giữ traceinput/output59–66 ở Storage620. Lượt đầu có importQdrantversioncheck; guardoffline đã chặn khi xác minh. Lượt chốt tắt riêng compatibilityprobe trong harness và chặn socket:0networkattempt/0DB/0LLM. Không đọc/ghi domainruntime hoặc tạo DBtest mới. Importtiktoken dùng encodingcache đã có, không tải tokenizer mới.

Apphash trước/sau giữ nguyên. Không fullPytest/benchmark vì không đổi ứng dụng; kết quả6203764PASS/18FAIL nền/17SKIP giữ là lịch sử. Không sửa canonical/nguồn/model/QG, khôngreindex/publish/restart/commit/push. Chưa có patch cho các hướng sửa trên trong phiên621.
