# Phiên 443 — Triển khai bốn ưu tiên chất lượng chat RAG

Ngày: 14/10/2026, Asia/Bangkok. Phạm vi được người dùng duyệt từ đề xuất phiên 442.

## Mục tiêu và giới hạn

Sửa kiểm chứng số/điều kiện theo vai trò; mở rộng parent-child cùng truy hồi đa biến thể hybrid; thêm corrective retrieval một lượt; đóng gói theo coverage và dedup span. Dùng skills backend-architect, rag-pipeline, clean-code-architect và chatbot-builder. Không thay provider/model/max_tokens/quota/reranker của người dùng, không reset/reindex/duyệt/xuất bản nguồn, không khôi phục DAG cho hỏi đáp. Backup tiếp tục tạm dừng.

## Mã thay đổi

- `backend/app/modules/rag/evidence_constraints.py`: vai trò typed cho điều kiện; tách shape ngày/số hiệu khỏi năm dữ liệu; giữ numeric guard cho ngưỡng, giờ, công thức và so sánh. Đại lượng hiện tại và alias phương thức dùng proof theo vai trò thay vì yêu cầu mọi số nền trong paragraph.
- `evidence_audit.py`, `evidence_indexed_audit.py`: contract audit truyền vai trò, bind nguyên văn proof; không chỉ dùng số trong nhãn LLM để quyết định số cần giữ.
- `evidence_dependencies.py`, `evidence_blocks.py`: closure cùng source identity, numbered parent + nhánh chữ cái qua trang, explicit parent units; atomic admission; greedy facet coverage có cost/relevance. Header dùng đầy đủ binding/index/source/hash, không source ID đơn lẻ.
- `evidence_search.py`, `evidence_pipeline.py`: variants đi qua hybrid thật và RRF; each session riêng, cùng snapshot. Bỏ semantic regenerate nhiều lần trên cùng context, thay một corrective search và chỉ re-propose khi có chứng cứ mới.
- `evidence_repair.py`: feedback không được bịa số/năm; giữ partial còn đúng immutable identity, kiểm chứng lại chứ không auto-approve. Nếu repair không giữ được claim an toàn, khôi phục context của partial trước đó.
- `evidence_passages.py`: exact span và containment dedup trong cùng binding/index/source/hash; giữ nội dung câu nguồn, không xuất bản nhãn/paraphrase model.
- `evidence_model.py`: instructions giữ purpose của điểm thi, intent/các vai trò và lỗi contract có tên contract/field (không raw payload).
- `evidence_scope.py`: tên trường lấy nguyên văn chỉ từ persona cấu hình không bị gán thành quote của câu hỏi; không thay trường đích bằng trường khác hoặc fallback khi thiếu proof cho một trường khác.
- `backend/tests/test_evidence_priorities_443.py`: các ca regression/negative và lỗi dịch vụ. `backend/scripts/verify_evidence_report.py`: đối soát report read-only với published raw spans/hash và decision integrity.
- Quy trình RAG, nhật ký, memory/snapshot và WORK_LOG cập nhật trong phiên này. Không sửa FE nên không chạy Vite/Biome.

## Kiểm chứng trước/sau

Test-first đã tái hiện năm điều kiện false-partial, thiếu cụm a/b, trích lặp, variants chưa gọi hybrid và early missing không tìm lại. Lần đầu 7 fail/1 pass gồm hai lỗi setup test quote; sửa setup để quote là proof nguồn thật, không coi hai lỗi setup là regression của runtime. Những negative ngưỡng/giờ/nhánh OR vẫn phải bị chặn.

Sau batch đầu: 121 kiểm thử trọng tâm đạt (bao gồm 25 ca của phiên này); Ruff toàn backend đạt, chỉ có cảnh báo quyền đọc các thư mục pytest cũ. Không sửa quyền/xóa thư mục cũ. Full suite đầu 1252 pass/11 fail/15 skip; đối chiếu XML cho thấy toàn bộ 11 tên fail trùng #441, không có fail mới.

Probe độc lập (không ghép thành benchmark):

- `admissions_eval443_probe3.json`: 5 partial do audit chọn vai trò value với paragraph rộng; 13 lấy được policy nhóm qua corrective nhưng audit đòi cả mã 402B; 38 scope502 trước retrieval. Những kết quả này dùng chẩn đoán, không là nghiệm thu.
- `admissions_eval443_probe3_second.json`: 5 supported 28,49s; 13 provider503, không quy thiếu nguồn; 38 JSON contract502. Cấu hình/publication/runtime không đổi trong lượt riêng đó.
- `admissions_eval443_probe_remaining.json`: 13 supported 23,5s với “một số ngành phù hợp”; 38 supported 29,98s có đúng phần dẫn mục2 và cả hai nhánh a/b, giữ 18,00/8,50, 16,50/6,50. Đây vẫn là probe riêng, không thay thế fresh20.

## Nghiệm thu cuối

Lượt `admissions_eval443_acceptance20.json` hoàn tất trên fingerprint riêng: 20 HTTP200/19 supported/1 missing (13). Chưa là lượt cuối. Câu13 missing do danh sách phương thức độc lập bị đóng gói cả nhóm trong câu hỏi focused, chiếm chỗ chính sách nhóm; corrective không có block mới. Sửa thêm phân biệt bullet độc lập với nhánh chữ cái. Test-first cho lỗi đóng gói này đã fail đúng nguyên nhân trước sửa.

Probe `admissions_eval443_focus_branch_probe.json`: 13 supported; 38 missing dù context có đủ cụm2+a/b. Verifier nhận các giá trị ở nhánh a/b nhưng không có phần dẫn trong OWN attached references, nên hiểu sai score prerequisite thành ranking score. Không quy lỗi này thành corpus thiếu nguồn. Sửa projection để attach/bind và hiển thị parent intro nguyên văn, không auto-approve; thêm test-first đã fail đúng nguyên nhân. RRF shortlist giữ đủ năm corpus winners trước preference seeds để ưu tiên nguồn không thành loại bỏ thông tin riêng.

Batch tiếp theo: 123 kiểm thử trọng tâm đạt, gồm27 ca mới; full1254 pass/11 baseline fail/15 skip. Lượt `admissions_eval443_verified20.json` có20 HTTP200/17 supported/2 partial(51,62)/1 missing(13), trên fingerprint riêng. Câu13 bị verifier từ chối vì thiếu proof năm trong OWN refs của hàng dữ liệu, dù header cùng nguồn đã có trong context. Câu51 bỏ giờ17:00 và62 thiếu thông tin áp dụng công thức. Đây không phải chứng nhận corpus thiếu nguồn.

Sửa cuối: auto-bind header mùa thật cùng full source identity vào projected claims, không public header hoặc ghi đè năm lịch sử. Cho phép năm mặc định đã validate trong corrective feedback. Hai regression mới gồm implicit year proof và legitimate default-year feedback; test năm đã fail trước sửa. Batch cuối 125 kiểm thử trọng tâm đạt, gồm29 ca mới. Ruff toàn backend đạt, các cảnh báo ACL thư mục pytest cũ không phải lint errors. Full cuối `pytest443_release.xml`: **1256 pass/11 fail/15 skip, 173,57s**. Đối chiếu toàn bộ tên fail với XML #441: danh sách giống hệt, không có test fail mới. FE không thay đổi trong phiên443 nên không chạy Vite/Biome.

Lượt nghiệm thu cuối `admissions_eval443_release20.json`: **20/20 HTTP200,18 supported,2 partial(6,9)**; không workflow execution. Mean26,80s,min16,86s,max42,09s.105 lượt GPT-OSS primary và1 Gemma fallback thành công; đây là usage theo conversation, không tổng số lượt embedding/reranker. Runtime/config/publication unchanged=true; publication fingerprint vẫn733f3faf2f247c16e3a2,20sources,epoch4. Không chỉnh runtime trong từng lượt20, không ghép/resume các lượt khác fingerprint.

Đối soát `scripts.verify_evidence_report` trên DB: **54/54 canonical citations đúng raw span/hash +1/1 reviewed-fact citation đúng immutable identity/giá trị hàng**; decision integrity không có lỗi. Kiểm tra này không xác nhận đủ ý hoặc đúng mọi quan hệ ngữ nghĩa. Không lấy HTTP200/supported/55trích dẫn đúng làm accuracy90%.

## Đối soát từng câu của lượt cuối

| Câu | Trạng thái runtime | Ghi nhận khi đọc đáp án |
| --- | --- | --- |
| 1 | supported | DQN, mùa2026 có căn cứ |
| 3 | supported | Hotline1800.55.88.49 từ nguồn, không áp oracle hotline cũ |
| 5 | supported | 5.173, không ép nhắc mã văn bản/ngày ban hành/4.500 nền |
| 6 | partial | Đã giữ53 đầu mùa/56 mã sau đó/28 bổ sung, nhưng audit đòi làm rõ cộng28 vào tổng dù câu hỏi không yêu cầu phép cộng; **false-partial/requirement drift còn lại** |
| 9 | partial | Đã cóPT1–PT5, mã/scope tương ứng và xét thẳng301, nhưng audit vẫn báo thiếu liệt kê; **false-partial/coverage-role mapping còn lại** |
| 11 | supported | Không áp học bạ vào nhóm giáo viên, giữ scope nguồn |
| 13 | supported | Lượt cuối dùng ví dụ hàngSư phạmTiếngAnh cóĐGNLĐHSPHN, đã gắn mùa2026. Không suy thành mọi ngành sư phạm. **Chưa phải câu trả lời chính sách nhóm đầy đủ/ổn định**; probe khác lấy được policy“một số ngành phù hợp” |
| 16 | supported | Giữ“nếu ngành cho phép/đáp ứng điều kiện”, không tự cộng học bạ vàTHPT |
| 19 | supported | 15/30 là điều kiện nguồn theo scope2026, không sàn mọi ngành |
| 22 | supported | Không đăng ký học bạ riêng trong đợt1 nhưng vẫn đăng ký nguyện vọng chung |
| 25 | supported | Nội dung không nhân hệ sốhai đúng quote; **đuôi câu“quy định của” bị dở do đơn vị qua trang**, cần xử lý tiếp tính liền mạch/đủ câu |
| 38 | supported | Đúng phần dẫnmục2+a/b; giữ18,00/8,50 vàGDTC16,50/6,50, không lẫn ranking với prerequisite |
| 48 | supported | Giữ22,5/30, công thức glyph nguyên bản và xu hướng ưu tiên; không còn câu lặp containment đã quan sát |
| 51 | supported | Có02/07 đến17giờ00 ngày14/07/2026; không chỉ ngày thiếu giờ |
| 62 | supported | Chỉ mô tả nội suy tuyến tính; **chưa đưa công thức dùng được/mốc bảng cần thiết**, không xem supported là đạt đủ câu hỏi tự tính |
| 66 | supported | Điểm2025 là lịch sử, không bảo đảm đậu2026 |
| 75 | supported | Nêu hệ thống tuyển sinh/Thông báo151 nhưng **chưa trả URL đăng ký cụ thể**; chưa chứng minh toàn corpus thiếu URL |
| 80 | supported | Đúng scope dự kiến toàn khóa4năm/4,5năm và số83–97/112,3; không gán thành học phí năm học |
| 81 | supported | Số học bổng2025 ghi rõ lịch sử, không cam kết2026/2027; có thêm chính sách hỗ trợsư phạm |
| 82 | supported | Giữ3.630.000/tháng,tối đa10tháng,cam kết và bồi hoàn theo scope nguồn |

**Kết luận nghiệm thu**: bốn cơ chế được triển khai và regression mới đạt; các lỗi chặn/truy hồi5/38 được cải thiện trong lượt cuối,13 có chứng cứ ví dụ nhưng vẫn cần ổn định coverage nhóm. Chưa đạt chứng nhận đúng/đủ toàn82 hoặc TM-08. Cần xử lý6/9false-refusal,13group coverage,25continuation,62formula và75URL trước khi tuyên bố chất lượng hoàn chỉnh. Không thêmGraphRAG/fine-tuning/đổi model/tắt guard để làm đẹp chỉ số. Latency quan sát26,80s so với29,65s ở441 không phải benchmark nhân quả vì mạng và kết quảmodel thay đổi.

11 lỗi nền cuối: consulting_dispatcher(admissions_export,regulations_export); publishing_v2_cutover_and_gc(gc_api,canary_policy); publishing_v2_decommissioning_and_system_gc(direct_upload_blocked,direct_upload_allowed,system_gc_audit); publishing_v2_e2e_canary(canary_and_rollback); rag_data_truth_and_lifecycle(reconciliation); trust_boundary_and_hitl(auth_cookie_actor); universal_tools(admissions_dynamic_facts). Tên test đầy đủ trong XML, không sửa ngoài phạm vi.

## Bài học và phần còn lại

Có căn cứ đúng nhưng audit chọn paragraph quá rộng vẫn có thể false-refuse; nên phân biệt trường dữ liệu/metadata/định danh thay vì tắt guardrail. Source-date shape chỉ hỗ trợ numeric obligation trong vai trò đại lượng hiện tại đã audited, không tự quyết định nguồn mới hơn thắng hoặc năm áp dụng. Closure là cấu trúc đọc trong RAG, không phải DAG workflow. Multi-query và greedy coverage là retrieval hints, verifier vẫn chịu trách nhiệm ngữ nghĩa. Mạng quốc tế chậm có thể gây timeout/fallback/provider503; không đổi thành trích đoạn answered hoặc gộp vào thiếu dữ liệu.
