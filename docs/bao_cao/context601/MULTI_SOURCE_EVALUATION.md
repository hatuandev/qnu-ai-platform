# Context601 — Thử nghiệm tài liệu thật nhiều năm

**Kết quả: 4/12 PASS, 8/12 FAIL (33,33%). Chưa nghiệm thu luồng nhiều nguồn/nhiều năm.**
Đây là tập thử riêng, không ghép điểm vào benchmark64. Nhãn được freeze trước inference, do Codex đối chiếu theo nguồn, chưa phải human holdout.

## Nguồn và phạm vi

| Nguồn local draft | Bytes | Canonical ký tự / units | Validator QNU Markdown/JSON | Wiki thật |
|---|---:|---:|---|---|
| Phuong huong tuyen sinh 2024_DHQN_final.docx | 44540 | 11287 / 208 | PASS về định dạng | UNAVAILABLE trước inference: unit dưới 3 ký tự |
| Báo cáo công tác Tư vấn tuyển sinh năm 2025_Du thao.docx | 131913 | 12184 / 149 | PASS về định dạng | UNAVAILABLE trước inference: unit dưới 3 ký tự |
| QNU_TuyenSinh_2026_VanBanThuyetMinh.docx | 43874 | 18370 / 56 | PASS về định dạng | READY:4 trang,2 Luna calls |

Báo cáo2025 có nhãn Dự thảo; nguồn2026 là bản thuyết minh biên tập. Phép thử chứng minh hành vi trên các văn bản này, không xác minh chúng là chính sách tuyển sinh hiện hành hoặc bản chính thức. Không dùng tên file để gán mọi dòng vào một năm.

Chuỗi đã chạy: bytes DOCX → DoclingOfficeParser → QNU structured builder → native-layout fidelity → Markdown/JSON validator → canonical projection/unit manifest → compiler extractive → evidence pipeline và prose fallback qua ModelOps thật. Mọi unit giữ locator/hash/span; toàn bộ bytes gốc không đổi.

Các adapter đọc local thay cho DB source/index records và vector anchors (BM25 thực). Không có approved fact records; snapshot local không phải snapshot được publish, không thực hiện upload/index/embedding/publication trong app. Actor thật được kiểm quyền trước inference. **Không phải full ingestion/vector/HTTP/browser E2E.**

## Kết quả theo ID

| ID | Nội dung kiểm tra | Kết quả | Nguyên nhân/kết quả quan sát |
|---|---|---|
| M01 | Chỉ tiêu và điều kiện2024 | FAIL | Không trả lời đủ tổng chỉ tiêu và điều kiện nguồn2024. |
| M02 | Năm ban hành khác năm dữ liệu2024 | FAIL | Không trả lời đủ nghị quyết/ngày và vai trò năm nguồn2024. |
| M03 | PT3 của2024 | PASS | Đủ hai đơn vị tổ chức kỳ thi cho PT3 của2024, chỉ dẫn đúng nguồn2024. |
| M04 | Số lượt tư vấn2025 và dự thảo | FAIL | Đã trích đúng ba số lượt nhưng kết thúc insufficient_context, chưa trả lời đủ điều kiện trạng thái nguồn. |
| M05 | Văn bản viện dẫn2024 trong báo cáo2025 | PASS | Đúng ngày nghị quyết2024, kế hoạch2025 và năm báo cáo2025, không lẫn vai trò năm. |
| M06 | Tình trạng dự thảo2025 | PASS | Trích đúng Dự thảo và tên báo cáo, không tự xác nhận bản chính thức. |
| M07 | Mức cập nhật trong cùng năm2026 | PASS | Đúng hai mức chỉ tiêu và hai thông báo cùng năm2026, không lấy số cũ làm mức cập nhật. |
| M08 | Ánh xạ PT3/PT4 và mã2026 | FAIL | Không chọn được đủ bằng chứng PT3/PT4/402A/402B từ nguồn2026, kết thúc insufficient_context. |
| M09 | So sánh phương thức2024/2026 | FAIL | Lỗi EVIDENCE_PLAN_SCOPE_INVALID, không phải câu trả lời so sánh hợp lệ. |
| M10 | So sánh chỉ tiêu hai năm | FAIL | Lỗi EVIDENCE_PLAN_SCOPE_INVALID, không phải câu trả lời hai năm hợp lệ. |
| M11 | Không có dữ liệu2027 | FAIL | Lỗi EVIDENCE_PLAN_SCOPE_INVALID, không được tính là từ chối đúng cho nguồn2027 thiếu dữ liệu. |
| M12 | Ngày viện dẫn khác năm báo cáo | FAIL | Lỗi EVIDENCE_PLAN_SCOPE_INVALID, chưa trả lời quan hệ ngày viện dẫn/năm báo cáo. |

14/14 citations được phát ra resolve chính xác về canonical, hash, revision, binding, index và span nguồn. Điều này không có nghĩa cả12 câu đúng hoặc Wiki nhiều năm đã đủ liên kết. Graph chỉ có4 trang của2026 và3 structural links;0 co-mention đa nguồn,0 identity approval. Không tuyên bố đã kiểm chứng graph giữa3 năm.

## Phân loại nguyên nhân

1. **Fragment cấu trúc:** 2024 có5 unit ngắn,2025 có1 unit ngắn. Compiler chặn trước inference, đúng guard hiện có. Đối chiếu OOXML cho thấy5 cửa sổ ba fragment có thể ghép trở về cùng một paragraph gốc; không tự gộp dữ liệu hay bỏ fragment trong phép thử. Một trường hợp cuối câu chưa xác minh bằng cửa sổ đó. Các lỗi M01/M02 không chứng minh tài liệu gốc thiếu dữ liệu; M04 đã có ba số lượt đúng nhưng vẫn bị trả partial/insufficient. Cần đối soát pipeline paragraph và scope binding, chưa đủ để đổ toàn bộ cho model hoặc parser.

2. **Nhận diện năm trong câu hỏi:** M09–M12 trả EVIDENCE_PLAN_SCOPE_INVALID, không phải từ chối đúng do thiếu nguồn. Câu freeze có dạng chữ liền năm, ví dụ `năm2027`. Validator dùng word boundary nên không ghi nhận literal year. Probe offline giữ nguyên kế hoạch năm đúng về ngữ nghĩa: cả4 câu original FAIL, thêm khoảng trắng thì4 control PASS. Không gọi lại LLM cho các control, không thay câu freeze hoặc ghi đè8 lỗi. Raw plan đầy đủ của các lỗi live chưa lưu trong trace, nên chưa loại trừ được sai khác planner khác ngoài lỗ hổng deterministic này.

3. **Chọn và kiểm chứng scope:** M08 vẫn từ chối dù Wiki2026 đã ready và canonical có hai ánh xạ cần hỏi. Đây là lý do không thể coi Wiki build PASS đồng nghĩa trả lời PASS. Cần thêm trace chọn đoạn/reject/coverage để chốt nguyên nhân chi tiết; không đoán thiếu context window.

4. **Sức chứa trang nguồn dài:** cẩm nang2025 được parse riêng, không nằm trong12 câu lõi. Probe compiler thật với selector xác định,0LLM: sau19 gói bị ValidationError `sections` vì1.301 vượt512. Bộ lõi dùng báo cáo2025, không thay nguồn rồi tuyên bố cẩm nang dài đã đạt.

## Cách xử lý tiếp có căn cứ

- Đối chiếu các fragment với paragraph OOXML bằng thứ tự và provenance duy nhất; chỉ hợp nhất các phần cùng paragraph/cell đã chứng minh được. Giữ run IDs/locator, ký hiệu, bảng và hash bản gốc. Unit ngắn hợp lệ phải có cách biểu diễn đúng vai trò; không xóa chúng hoặc giảm guard chung để che lỗi. Nếu canonical thay đổi, cần revision mới trong một lượt được cho phép riêng; hiện tại không reindex.
- Tách bước nhận diện literal year khỏi việc xác định vai trò năm. Hỗ trợ năm sát chữ, vẫn phân biệt mã định danh/số dài, năm viện dẫn và năm dữ liệu; regression cho cả positive/negative. Không sửa câu benchmark thành dễ hơn để lấy PASS.
- Chia inventory nguồn dài thành các trang/phần có giới hạn, liên kết continuation do server tạo và bảo toàn mọi unit. Không tăng vô hạn512 hoặc cắt phần dư.
- Tăng bằng chứng chẩn đoán cho selector/audit ở metadata an toàn, rồi xử lý coverage/điều kiện của P07/P08/P16 và M08. Không ghi prompt/corpus/private output vào Git/log công khai.

## Inference, an toàn và giới hạn

- Runner thực chạy đủ12, exit0 là hoàn thành orchestration; **acceptance vẫn FAIL (4 PASS/8 FAIL)**. Offline đối chiếu response hashes/citations hoàn thành exit0; đó không phải kết luận chất lượng PASS.
- QA có102 usage records và compiler có2; chỉ Luna,0fallback. QA:540.666 input/24.310 output tokens; compiler:10.120 input/991 output tokens. Không giả định chi phí tiền khi thiếu đơn giá.
- Chạy nối tiếp sau64 và postcheck; không có lượt model phụ trong lúc64. Thời gian M08 gồm cả evidence và prose fallback, không được gọi nhầm là một request provider30s timeout.
- Cả3 bytes nguồn giữ hash; app/source/model/config/index/publication postcheck PASS.2.943 vector payloads khớp toàn bộ trước/sau,0retrievable. Không tự approve quan hệ, source unknown, draft hoặc publication.
- Chưa render DOCX/PDF để kiểm trang/ảnh; parser cảnh báo thiếu Office converter cho DrawingML. Validator định dạng không chứng minh đầy đủ nội dung/ảnh hoặc sẵn sàng production.
- DB test đã xóa sau xác minh exact name/nonce. Storage và evidence riêng giữ theo chính sách bảo vệ có từ trước; không thử xóa vòng qua guard. LLM usage/audit giữ nguyên.

Artifacts chi tiết (ignored): `backend/storage/context601/multi-source-core/`, `multi-source-v2/handbook-probe.json` và `acceptance-release/postcheck-after-multi.json`. Không đưa corpus, prompt, response private hoặc credentials vào báo cáo Git.
