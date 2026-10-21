# Context583 — Benchmark RAG 64 câu trên PDF staging

Kết quả: **54/60 = 90.0% câu tri thức**, 4/4 câu hội thoại. Mục tiêu 85%: **ĐẠT**; đồng thời phải đạt ít nhất 43/50 câu có đáp án. PDF đạt 44/50 câu có đáp án và 10/10 câu cần từ chối/làm rõ. Đủ 64/64 ID, không thiếu/trùng; lỗi runtime/timeout vẫn tính FAIL.

DOCX Context576 lịch sử: **59/60 = 98,33%**, social 4/4. So từng ID: chuyển FAIL→PASS: **P06**; chuyển PASS→FAIL: **P01, P05, P07, P09, P10, P16**. Cùng 64 câu, rubric, giá trị kỳ vọng và actual Luna; vị trí gold đã ánh xạ sang PDF. Không thể quy toàn bộ chênh lệch cho định dạng vì PDF dùng candidate service, DOCX lịch sử dùng published assistant API và mã parser khác phiên bản.

## Phạm vi và cách chạy

- Nguồn PDF 18 trang; binding `bnd_12190866d5ec`, revision `ks_rev_fef00606f91f`, index `idx_rev_bba8c17700d0`, generation `vg_a6e3190d11af`.
- SHA256 PDF `082c412e145a9ef39ae50110ae16cc80c17d612e2f0e00f9d16ee78c7c1c3b02`; canonical `ad0dc2900b502fbe84ed5549263be49f4d55d4df5c17001414ea2f748d2c9152`.
- 327 chunks/415 facts/327 điểm Qdrant staging; 0 điểm retrievable, binding chưa có active index. Không xuất bản để chạy test.
- Xác minh DB, MinIO, Qdrant loopback trong development; actor được xác thực và có quyền. `resolve_candidate_snapshot` kiểm tra source/index/fact/hash, rollback transaction khóa; truyền snapshot do server tạo vào `rag_service.ask` thật.
- Dùng runtime profile persisted của admissions, cùng chuẩn bị input/history và tham số generation, 6 lượt tri thức gần nhất cho follow-up. Đây là benchmark service có retrieval/rerank/LLM thật, **không phải HTTP/chat UI E2E**, không mock hay override ứng dụng.
- Primary giữ `cx/gpt-6-luna`, fallback cấu hình vẫn Qwen. Giới hạn chat provider Luna trong context kiểm thử bằng chính sách server có sẵn, giống lượt DOCX; không đổi cấu hình DB/model. Embedding/reranker dùng route thật hiện tại.
- Freeze 64 câu trước inference; giữ nguyên câu hỏi/criteria/rubric/expected values. 124 ánh xạ fact/span hoàn tất, 0 chưa đối chiếu. Chỉ chuẩn hóa khoảng trắng/bullet để so vị trí; quote nguồn chạy thật giữ nguyên. Hai ghi chú trùng chữ được phân biệt theo bảng/vị trí; hình có receipt xác nhận riêng của PDF. Không suy gold IDs cũ sang PDF.
- Chấm 29 câu ô dữ liệu bằng đúng fact/column/year/value/entity và citation row; 35 câu còn lại do Codex đọc câu trả lời cùng nguồn/rubric, không gọi judge LLM. Nhãn vẫn draft agent-source-checked, chưa human holdout; không phải nghiệm thu production.

## Kết quả theo nhóm

| Nhóm | PASS/tổng | Tỷ lệ |
| --- | --- | --- |
| scalar | 16/16 | 100.0% |
| other_table | 4/4 | 100.0% |
| multi | 5/5 | 100.0% |
| enumeration | 1/1 | 100.0% |
| followup | 8/8 | 100.0% |
| prose | 10/16 | 62.5% |
| negative | 10/10 | 100.0% |
| social | 4/4 | 100.0% |

## Các câu FAIL

| ID | Loại | Bằng chứng/nguyên nhân quan sát |
| --- | --- | --- |
| P01 | over_refusal | Nguồn có giới hạn chỉ mô phỏng nhưng câu trả lời từ chối, không đáp ứng rubric. VISIBLE_ANSWER_NOT_SUPPORTED; audit thấy 3 assertion thiếu bằng chứng; prose fallback NO_UNAMBIGUOUS_BOUND_PROSE. |
| P05 | over_refusal | Từ chối NO_COMPATIBLE_FACT_EVIDENCE, không nêu được Ước tính 2027 chỉ là kế hoạch và không áp sang Ghi nhận 2026; nguồn có đủ quy ước. |
| P07 | missing_essential_condition | Đúng biên bản trực tuyến/30ngày/không miễn an toàn/không nhóm A, nhưng bỏ điều kiện chữ ký chậm vì cơ sở tạm đóng, có nhật ký và xác nhận giảng viên cùng kỳ mà rubric yêu cầu. |
| P09 | runtime_error | Lỗi service/timeout/runtime: ROW_ANSWER_SOURCE_INVALID; không được tính là từ chối đúng. |
| P10 | runtime_error | Lỗi service/timeout/runtime: ROW_ANSWER_SOURCE_INVALID; không được tính là từ chối đúng. |
| P16 | runtime_error | Lỗi service/timeout/runtime: ALL_PROVIDERS_UNAVAILABLE; không được tính là từ chối đúng. |

Các mã audit/selector ở đây là điểm chặn quan sát được, chưa đủ để quy nguyên nhân duy nhất cho parser hoặc model. Không sửa mã hoặc nới Quality Gate trong lượt đo.

## Model, citation và thời gian

- Usage: 105 bản ghi, 105 success, 0 fallback; model counts `{"gpt-6-luna": 105}`. Không có model ngoài Luna trong log của các session benchmark.
- 105 là số usage thành công ghi nhận, không phải tổng số HTTP attempts; lượt timeout có thể không có usage/token log.
- Tokens quan sát: input 529632, output 25436; max prompt 9126. Không suy chi phí khi chưa đối soát đơn giá.
- Citation hash/revision/span/quote: 119/119 hợp lệ. Citation resolve đúng không đồng nghĩa câu trả lời đủ hoặc đúng; rubric vẫn chấm riêng.
- P16 trả `ALL_PROVIDERS_UNAVAILABLE`; log inference ghi một `ReadTimeout` trên route Luna. Không có `MODEL_CONTEXT_EXCEEDED`; max prompt quan sát 9.126 tokens. Đây là timeout provider quan sát được, không phải timeout 150s của runner hay bằng chứng Qwen32k thiếu context.
- Runtime errors: P09, P10, P16. Tri thức p50 515.86 ms, p95 44240.43 ms, max 57053.42 ms. Không so latency trực tiếp với DOCX vì ranh giới đo khác.

## Kiểm chứng và bảo toàn

- Runner exit 0; scorer exit 0. Mốc bắt đầu/kết thúc UTC: 2026-10-21T07:10:02.877692+00:00 → 2026-10-21T07:22:02.270005+00:00.
- Hash mọi file Python app/tests, toàn bộ row seals source/index/generation/assistant/provider config và Qdrant payload/count khớp trước/sau. Raw PDF trong Storage khớp hash; nguồn vẫn chưa publish. Các thay đổi chưa commit từ Context578–582 được giữ nguyên.
- Inference được ghi lease/usage audit bình thường; không chỉnh ModelOps policy/config. Không tạo conversation/gap test persisted hoặc DB/Storage runtime mới; kiểm sau không còn thread/message theo session IDs. Giữ usage và bằng chứng benchmark riêng trong thư mục ignored.
- Lượt harness đầu bị dừng exit1 vì đặt transaction read-only khiến ModelOps không khóa/ghi lease được; 0 usage ghi nhận. Lưu nguyên kết quả trong `backend/storage/context583/harness-readonly-attempt/`, đánh dấu invalid harness và không trộn điểm. Chỉ chỉnh runner kiểm thử, rồi chạy riêng đầy đủ 64 câu. Không chọn điểm tốt nhất giữa nhiều lượt chất lượng.
- Full Pytest hiện tại: **NOT RUN**, không sửa ứng dụng. Context582 lịch sử vẫn **FAIL18**, 2.985 PASS/17 SKIP, không đổi thành PASS của lượt này. FE/build, dense/hybrid ablation, Hit@K/Recall@K/MRR và published HTTP/UI E2E: **NOT RUN**.
- Không commit/push/reindex/publish/restart/deploy. Không thử lại xóa Storage đã bị policy chặn ở phiên trước.

## Đối chiếu từng test ID

| ID | DOCX576 lịch sử | PDF583 staging | Đánh giá hiện tại |
| --- | --- | --- | --- |
| N01 | PASS | PASS | Đủ ô nguồn, đúng tọa độ/giá trị/phạm vi và trích dẫn. |
| N02 | PASS | PASS | Đủ ô nguồn, đúng tọa độ/giá trị/phạm vi và trích dẫn. |
| N03 | PASS | PASS | Đủ ô nguồn, đúng tọa độ/giá trị/phạm vi và trích dẫn. |
| N04 | PASS | PASS | Đủ ô nguồn, đúng tọa độ/giá trị/phạm vi và trích dẫn. |
| N05 | PASS | PASS | Đủ ô nguồn, đúng tọa độ/giá trị/phạm vi và trích dẫn. |
| N06 | PASS | PASS | Đủ ô nguồn, đúng tọa độ/giá trị/phạm vi và trích dẫn. |
| N07 | PASS | PASS | Đủ ô nguồn, đúng tọa độ/giá trị/phạm vi và trích dẫn. |
| N08 | PASS | PASS | Đủ ô nguồn, đúng tọa độ/giá trị/phạm vi và trích dẫn. |
| N09 | PASS | PASS | Đủ ô nguồn, đúng tọa độ/giá trị/phạm vi và trích dẫn. |
| N10 | PASS | PASS | Đủ ô nguồn, đúng tọa độ/giá trị/phạm vi và trích dẫn. |
| N11 | PASS | PASS | Đủ ô nguồn, đúng tọa độ/giá trị/phạm vi và trích dẫn. |
| N12 | PASS | PASS | Đủ ô nguồn, đúng tọa độ/giá trị/phạm vi và trích dẫn. |
| N13 | PASS | PASS | Đủ ô nguồn, đúng tọa độ/giá trị/phạm vi và trích dẫn. |
| N14 | PASS | PASS | Đủ ô nguồn, đúng tọa độ/giá trị/phạm vi và trích dẫn. |
| N15 | PASS | PASS | Đủ ô nguồn, đúng tọa độ/giá trị/phạm vi và trích dẫn. |
| N16 | PASS | PASS | Đủ ô nguồn, đúng tọa độ/giá trị/phạm vi và trích dẫn. |
| N17 | PASS | PASS | Đúng chủ trì P.ĐT và hạn 30/11/2026; trích dẫn đúng dòng NV-01 và header. |
| N18 | PASS | PASS | Nêu nguyên điều kiện NV-28: Theo đủ điều kiện Phụ lục II; không khẳng định chỉ có hồ sơ là đạt; trích dẫn đúng dòng. |
| N19 | PASS | PASS | Nêu đúng 0 và phạm vi số giờ vượt mức nhóm A năm 2026 có chứng cứ bằng 0; trích dẫn đúng CT-01. |
| N20 | PASS | PASS | CS-02 là Thiết bị mô phỏng, trạng thái Cần làm rõ; trích dẫn đúng dòng/header. |
| M01 | PASS | PASS | Đủ ô nguồn, đúng tọa độ/giá trị/phạm vi và trích dẫn. |
| M02 | PASS | PASS | Đủ ô nguồn, đúng tọa độ/giá trị/phạm vi và trích dẫn. |
| M03 | PASS | PASS | Đủ ô nguồn, đúng tọa độ/giá trị/phạm vi và trích dẫn. |
| M04 | PASS | PASS | Đủ ô nguồn, đúng tọa độ/giá trị/phạm vi và trích dẫn. |
| M05 | PASS | PASS | Đủ 12 cặp mã/tên đúng từng dòng Bảng 1, giữ số 0 đầu và dấu nối; không thêm dòng tổng; 12 trích dẫn đúng. |
| M06 | PASS | PASS | Đủ ô nguồn, đúng tọa độ/giá trị/phạm vi và trích dẫn. |
| F01 | PASS | PASS | Đủ ô nguồn, đúng tọa độ/giá trị/phạm vi và trích dẫn. |
| F02 | PASS | PASS | Đủ ô nguồn, đúng tọa độ/giá trị/phạm vi và trích dẫn. |
| F03 | PASS | PASS | Đủ ô nguồn, đúng tọa độ/giá trị/phạm vi và trích dẫn. |
| F04 | PASS | PASS | Đủ ô nguồn, đúng tọa độ/giá trị/phạm vi và trích dẫn. |
| F05 | PASS | PASS | Đủ ô nguồn, đúng tọa độ/giá trị/phạm vi và trích dẫn. |
| F06 | PASS | PASS | Đủ ô nguồn, đúng tọa độ/giá trị/phạm vi và trích dẫn. |
| F07 | PASS | PASS | Đủ ô nguồn, đúng tọa độ/giá trị/phạm vi và trích dẫn. |
| F08 | PASS | PASS | Đủ ô nguồn, đúng tọa độ/giá trị/phạm vi và trích dẫn. |
| P01 | PASS | FAIL | Nguồn có giới hạn chỉ mô phỏng nhưng câu trả lời từ chối, không đáp ứng rubric. VISIBLE_ANSWER_NOT_SUPPORTED; audit thấy 3 assertion thiếu bằng chứng; prose fallback NO_UNAMBIGUOUS_BOUND_PROSE. |
| P02 | PASS | PASS | Đúng khoảng 01/09/2026–31/08/2027 và phân biệt năm dương lịch; trích dẫn exact câu nguồn hỗ trợ, dù khác gold block gợi ý. Số 1 cuối câu là dấu chú thích từ PDF, không thay dữ kiện. |
| P03 | PASS | PASS | Giữ đúng thứ tự ba nguồn chứng cứ cùng điều kiện bản tổng hợp không vượt chứng cứ gốc; các câu đều có exact source citations. |
| P04 | PASS | PASS | Giữ đúng sổ xác nhận phòng máy và scope chỉ AM-0007; loại trừ rõ AM-0070; source quote khớp. |
| P05 | PASS | FAIL | Từ chối NO_COMPATIBLE_FACT_EVIDENCE, không nêu được Ước tính 2027 chỉ là kế hoạch và không áp sang Ghi nhận 2026; nguồn có đủ quy ước. |
| P06 | FAIL | PASS | Đủ đối tượng nhóm A/kế hoạch2027, tối đa15ngày làm việc từ hạn ban đầu, lịch kiểm định trùng đợt khóa và quyết định P.ĐT; loại trừ chỉ tiêu SV/nhóm B; exact citations hỗ trợ. |
| P07 | PASS | FAIL | Đúng biên bản trực tuyến/30ngày/không miễn an toàn/không nhóm A, nhưng bỏ điều kiện chữ ký chậm vì cơ sở tạm đóng, có nhật ký và xác nhận giảng viên cùng kỳ mà rubric yêu cầu. |
| P08 | PASS | PASS | Đúng mã là chuỗi, không lược số0 đầu hoặc dấu nối, source rows và footnote hỗ trợ; không đổi 0012 hoặc AM-0007. |
| P09 | PASS | FAIL | Lỗi service/timeout/runtime: ROW_ANSWER_SOURCE_INVALID; không được tính là từ chối đúng. |
| P10 | PASS | FAIL | Lỗi service/timeout/runtime: ROW_ANSWER_SOURCE_INVALID; không được tính là từ chối đúng. |
| P11 | PASS | PASS | Giữ riêng >15giờ/người cho giảng viên có hợp đồng và >=15giờ/khoa cho khoa chuyên môn; đúng chủ thể/ngưỡng/đơn vị/điều kiện, source rows hỗ trợ. |
| P12 | PASS | PASS | Đúng Q=0,45A+0,35B+0,20C; >=80% chứng cứ đủ điều kiện và cả3biến số xác thực; thiếu thì Chưa đủ điều kiện tính, không gán0; citations đủ. |
| P13 | PASS | PASS | Đúng Khoa/Viện→P.ĐT→Hội đồng và đường hồi tiếp yêu cầu hiệu chỉnh có biên bản; exact citations từ nội dung hình đã có receipt và note PDF. |
| P14 | PASS | PASS | Nêu đúng mỗi ghi chú chỉ áp dụng cho bảng đứng ngay trước, không áp dụng chéo do trùng chữ; exact source sentence hỗ trợ, không suy CS-02 sang TT-02. |
| P15 | PASS | PASS | Đúng ban hành18/10/2026 và bắt đầu dùng mô phỏng01/11/2026; không đồng nhất hai mốc, source sentence trực tiếp hỗ trợ. |
| P16 | PASS | FAIL | Lỗi service/timeout/runtime: ALL_PROVIDERS_UNAVAILABLE; không được tính là từ chối đúng. |
| X01 | PASS | PASS | Từ chối số liệu năm2099, không mượn số/năm/điều kiện khác; NO_COMPATIBLE_FACT_EVIDENCE phù hợp snapshot. |
| X02 | PASS | PASS | ENTITY_CODE_UNRESOLVED, không đưa số hay thay AM-0099 bằng mã gần giống. |
| X03 | PASS | PASS | ENTITY_CODE_UNRESOLVED, không tự sửa AM-07 thành AM-0007 hoặc AM-0070. |
| X04 | PASS | PASS | Yêu cầu xác định đại lượng chỉ tiêu/ghi nhận, không chọn tùy tiện một số. |
| X05 | PASS | PASS | Nêu rõ đơn vị nguồn SV khác lớp, chưa có quy đổi, không dùng cùng số cho đơn vị khác. |
| X06 | PASS | PASS | Yêu cầu xác định năm dữ liệu trước khi chọn số, không chọn mặc định. |
| X07 | PASS | PASS | Nêu / CT-06 chưa được công bố ý nghĩa, phải giữ nguyên và không tự diễn giải; không đưa số giờ hay gán0. Trích dẫn đúng chú giải và footnote. |
| X08 | PASS | PASS | Phân biệt sốước tính/dựkiến với ghi nhận đã nghiệm thu, không dùng sai vai trò số2027. |
| X09 | PASS | PASS | Nêu chỉ tính khi cảA/B/C có số xác thực, thiếu bất kỳ biến thì chưa đủ điều kiện tính/không gán0; không bịa Q, source citation đúng. |
| X10 | PASS | PASS | Không đưa điểm chuẩn Ykhoa2028 hoặc dữ liệu kho cũ; từ chối vì chưa có căn cứ phù hợp với ngữ cảnh/năm được hỏi. |
| S01 | PASS | PASS | Đúng loại hội thoại, không báo thiếu tri thức; trace không retrieval/router model và usage không có model call cho session. |
| S02 | PASS | PASS | Đúng loại hội thoại, không báo thiếu tri thức; trace không retrieval/router model và usage không có model call cho session. |
| S03 | PASS | PASS | Đúng loại hội thoại, không báo thiếu tri thức; trace không retrieval/router model và usage không có model call cho session. |
| S04 | PASS | PASS | Đúng loại hội thoại, không báo thiếu tri thức; trace không retrieval/router model và usage không có model call cho session. |

Bằng chứng riêng (ignored): `backend/storage/context583/manifest-frozen.json`, `mapping-final.json`, `responses-private.json`, `adjudications.json`, `labels-final.json`, `summary.json`, `comparison.json`, `single-model-verified.json`, `postcheck.json`. Không chép corpus/prompt riêng/credential vào báo cáo Git.
