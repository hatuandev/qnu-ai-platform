# Phiên 415 Đề xuất xử lý chatbot sau khi đổi model

## Mục tiêu và phạm vi

Người dùng đã lưu primary `gh/gpt-6-luna[1m]`, fallback `gemini-3.1-flash-lite`, yêu cầu xem vấn đề trong quá trình test và đề xuất giải pháp. Áp dụng hướng dẫn chatbot-builder/RAG/ModelOps để kiểm tra theo nguồn và trace, không coi status answered là đáp án đúng. Chỉ chẩn đoán và đề xuất; không sửa runtime, cấu hình, schema, embedding, nguồn, duyệt hay tái xuất bản.

## Kiểm tra hiện trạng và kết quả mới

Cấu hình đã lưu: primary như trên, temperature0.2/max_tokens4000/thinking0; workflow admissions-assistant, published_workflow_version_id null. Reranker đang là bge-reranker-v2-m3/prov_cloudflare. Readiness78%, blocker ready_documents0. Kho thực tế có19 binding/source/index đã xuất bản, epoch3/genvg_21324678abcf; bảng KnowledgeDocument legacy có0record.

Dùng bộ82câu đã trích xuất ở phiên412, chỉ gửi nguyên câu hỏi, không đáp án. Test lại14câu trọng yếu trên DAG, mỗi câu hội thoại mới, chạy tuần tự để hạn chế nhiễu key contention. Giữ cache hiện tại, không benchmark cold-cache, không chạy Ragas/full82 trong phiên này. Các con số phiên412 không được coi là điểm chất lượng của model mới.

Kết quả batch14:11answered,1insufficient_context,2HTTP500. Đây không phải11câu đúng. Usage thật:10inference custom/gpt-6-luna/noFallback,1Gemini/gemini-3.1-flash-lite/fallback; quota deterministic và2câu lỗi không có inference success. Lượt đầu chuyển Gemini vì qnu9routerReadTimeout; cascade còn thử nhầm alias gh/gpt-6-luna[1m] trên provider vLLM embedding/reranker và bị modelnotfound. Gemini hiện active và có khóa thật (JSON1/relational1); không còn tình trạng thiếu key phiên413.

| Câu | Quan sát mới | Đối chiếu và giới hạn |
| ---: | --- | --- |
| 1,3 | DQN/hotline1800.55.88.49, có citations | Đúng nội dung trọng tâm; câu1 dùng Gemini fallback |
| 5 | Thiếu căn cứ tổng chỉ tiêu2026 | Canonical active ghi5.173; temporal fact gate đóng trước hybrid retrieval; không do khả năng LLM |
| 9 | Liệt kê5phương thức+trực tiếp thành6 | Cần thống nhất cách đếm/mã theo đúng nguồn; không tự coi khác cách đếm là sai toàn câu |
| 21 | Trả sư phạm không học bạ nhưng chọn2025 | Câu gốc không có năm; cần mùa tuyển sinh cấu hình hoặc hỏi rõ, không tự mặc định năm cũ |
| 25 | Không xác nhận hệ số2 từ tổ hợp môn | An toàn hơn khẳng định vô căn cứ trước đó; chưa đạt đầy đủ FAQ |
| 39 | GDMN có năng khiếu, nêu2026 | Đúng nội dung trọng tâm |
| 41 | Không thấy tiêu chuẩn chiều cao/cân nặng | Canonical nguồn cập nhật có nam1,65m/45kg, nữ1,55m/40kg;5retrievedcontexts không chứa đoạn đó |
| 42 | Chưa có mức điểm sàn cụ thể | Nguồn active TBđiểm sàn26 có20 và điều kiện13,34; retrieval lấy văn bản đầu mùa thay vì bảng chuyên đề |
| 51,68 | Batch đầu HTTP500 | RetryAPI200:51noanswer dù canonical có02/7–14/7;68trả đúng13/8–21/8vàphân biệt nhập học24–28/8 |
| 76–78 | Không lấy lịch nhập học/15NV/300k để gán cho bổ sung | An toàn hơn batch cũ; vẫn chưa trả được chi tiếtFAQ do thiếu thông báo chuyên đề trong danh mục nguồn |

Hai lỗi500 có correlation IDs corr_51bdaa5dd6da/corr_a22538683359; workflow c7d8e6f3-e4a7-4ee7-a644-d81c2c11a303 và8bb61da6-22e0-44ec-ab2e-d1f69ca23ba1 cònrunning/errornull/nodes0. Gọi service trực tiếp câu51 không tái hiện exception; retryhaiHTTPAPI đều200. Chưa có stack API để kết luận gốc; không quy lỗi500 cho model hoặc Redis. Workflow chưa được finalized đúng là bằng chứng cần xử lý ở boundary lỗi/cancel.

## Đề xuất theo thứ tự triển khai

### 1 Đồng bộ trạng thái sẵn sàng và cấu hình trợ lý

Readiness dùng cùng published snapshot với RAG: tenant/workspace, generationactive, bindingactive, source/indexđãduyệt/parity hợp lệ. Có nguồn đang serving là xét được; không bắt mọi nguồn chưa xuất bản phải hoàn tất. Giữ đường legacy tương thích chỉ khi collection thực sự dùng legacy. Không tạo rowlegacy giả để tăng đếm hay bỏ kiểm tra an toàn.

FE lưu chat model phải bảo toàn toàn bộ reranker_policy, nhất làprovider_id; hiện FE dựng object mới thiếu field và BE defaultCloudflare. Chọn provider/model thành tuple từ catalogue động, validation đúng role; bge-reranker-v2-m3 thuộc catalogue máyQNU, không catalogueCloudflare hiện tại. Cần người quản trị chọn cặp hợp lệ, hoặc giữ cặp đã lưu trước nếu chỉ sửa chat; không tự chuyển provider bằng tên cứng. Model check không chỉ có primary/fallbackstrings: kiểm tra provider/key/capability và health record còn hợp lệ với fingerprint cấu hình. Không gọi LLMtốnphí ở mỗiGETreadiness.

Pin workflow version sau khi người dùng xuất bản để benchmark/replay biết đúng workflow; không tự tái xuất bản trong lượt chẩn đoán này.

### 2 Số liệu có căn cứ cả trong bảng và đoạn văn

Hợp nhất evidence resolver cho facts/bảng/prose đã xuất bản. Fact tuple gồm đối tượng, thuộc tính, giá trị, nămápdụng, phươngthức, đợt, đơnvị, điều kiện, nguồn/page/span/revision. Giá trị tổng chỉ tiêu5.173 ở prose phải có đường evidence tương đương fact-table, không kết thúc missing chỉ vì chưa có cell trong bảng.

Ưu tiên parsing cấu trúc câu/đoạn và schema thuật ngữ cấu hình trongDB, không từ điển vá riêng từng câu. Model có thể đề xuất claim/span, nhưng giá trị phải khớp span gốc và context được kiểm chứng; không lấy cùng con số ở chỗ khác làm bằng chứng. Evidence chưa xác minh hoặc xung đột chuyển review/clarify/noanswer, không âm thầm ghi facts production hoặc điền các ô bảng trống. Không tái OCR/reembed toàn kho nếu chỉ thay retrieval/gate.

### 3 Truy xuất đúng mùa tuyển sinh và đúng loại sự kiện

Query planner tách object/attribute/year/method/round/eventtype/units. Khi câu không có năm, lấy mùa nghiệp vụ mà quản trị đã cấu hình và nêu rõ năm, hoặc hỏi làm rõ; không mặc định tất cả câu theo năm máy tính. Tách issueyear của văn bản khỏi nămápdụng dữ liệu. Lọc tương thích trước ranking: không thay điểm sàn bằng điểm chuẩn, đợt chính bằng bổ sung, phíthi bằng phíxéttuyển, xácnhận trênBộ bằng nhậphọcQNU.

Ưu tiên nguồn chuyên đề đang hiệu lực so với bản đầu mùa khi cùng context; không chọn đơn giản file có năm mới nhất hoặc filename chứa2026. Quan hệ replaces/supersedes và scope theo metadata quản trị/evidence, giữ nguồn lịch sử để trả câu năm cũ. Nguồn mâu thuẫn không đủ hiệu lực phân xử thì báo cần xác nhận thay vì đoán.

Mở rộng context có mục tiêu theo điều/mục/header/parentchunk và entityattribute để lấy đoạn thể hình cùng nguồn; thêm coverage check và tối đa1vòngretrieve bổ sung có giới hạn thời gian/token. Không chỉ tăngtop_k/max_tokens hoặc đưa toàn bộ19tài liệu vào prompt.

### 4 Một quyết định trả lời chung cho RAG và DAG

Chuẩn hóa AnswerDecision supported/partial/missing/conflict/clarify với claim_evidence binding. RAG tạo quyết định, DAG giữ nguyên semantics; citations phải đi theo claim đủ căn cứ, không sửa bằng cách tắtguard hoặc đính kèm trích dẫn không liên quan. Với số liệu, dùngDecimal/unit/time normalization và tupleexact cho renderdeterministic. Với chính sách/phủđịnh/ngoạilệ cần quan hệ mệnhđề–evidence, không chỉ overlap từ/số trong cảcontext.

Phân biệt dữ liệu tồn tại trong kho nhưng truy xuất chưa đủ với thật sự chưa có nguồn: câu trả lời không được nói trường chưa công bố chỉ vì context thiếu. Statusanswered không được dùng cho câu chưa trả được thông tin trọng tâm rồi dẫn sang thông báo cũ. Dùng missing/partial có lýdo rõ; được hỏi thêm hoặc hướng dẫn xem nguồn chính thức.

No-answer lấy đầu mối tuyển sinh từ cấu hìnhDB/nguồnđãxácminh, thống nhấtRAG/DAG; mẫu hiện còn0256.3846.156 trong khi nguồn cập nhật dùng1800.55.88.49. Không hardcode hotline mới ở nhiều file. Giao diện thử chat hiện modelrequested/served/provider/fallbackreason và evidence, không chỉ tên cấu hình.

### 5 Ổn định timeout, định tuyến và vòng đời workflow

Persist primary_provider_id/fallback_provider_id kèm alias; danh sách failover đúng policy và rolechat. Không thử alias9router trên server chỉ cung cấpembedding/reranker vì loạiendpointcustom/vLLM nhận tên tùy ý. Provider roles/capabilities dùng catalogueDB, không gán cứng tên model. Timeout điều chỉnh theo dữ liệu latency/provider/model và deadline toànworkflow; không timeoutcứng15s cho mọi tác vụ hoặc chờ vôhạn. Hiển thị fallback thật thay vì giữ tênprimary trên UI.

Boundaryworkflow bao cả setup/flush/engine/finalize: lỗi/cancel/timeout rollbacktransaction lỗi rồi sessionmới ghi failed/cancelled và correlationid. Trace giai đoạn đầu trước node cần ghi đủ; running chỉ khi có heartbeat/lease sống, reconcile abandoned không tự replay hành động có sideeffect. Cần capturestack500 bằng logJSONsanitize trong lần tái hiện tiếp theo; chưa khẳng định nguyên nhân DB/network từ các dữ liệu hiện có.

### 6 Bổ sung nguồn thiếu và kiểm thử độc lập

Nhóm xét tuyển bổ sung cuối mùa cần các thông báo chính thức tương ứng151/158 và phụ lụcđúngđợt; catalogue hiện19nguồn chưa chứa các thông báo này. FAQ có thể được duyệt thành nguồn phục vụ sau đối soát nhưng không dùng bộđápánđangtest làm evidence cho chính bài đánh giá. Không lấy lịch/giátrịđợt khác để lấp chỗ trống.

Sau sửa1–5, chạy full82 trên publishedsnapshot và config/workflowfingerprint cốđịnh, ghi servedmodel; thêm biến thể tương đương, đa lượt, nămcũ, thiếu năm, ngoàiphạmvi, thiếunguồn, conflict, injection, providerdown/timeout/cancel. Tách câuđúng/cósai/noanswerđúng/noanswersai/lỗikỹthuật; không lấy tỷlệanswered làmaccuracy. Ragas chỉ công bố khi thực sự chạy và đốisoátgoldreferences bằng nguồnchínhthức.

## Tiêu chí nghiệm thu đề xuất

- Readiness nhìn đúng nguồn đangserving và partialpublication; không falseblock0documents khi19bindinghợp lệ, không bypassreview/parity/scope.
- Lưu chatmodel không thay rerankerprovider; model/provider thật hiển thị và fallback theo policy.
- Các câu5/41/42/51 lấy đúng5.173/thểhình/sàn20+điềukiện/lịch02–14/7 từ sourcepage đúngcontext; nếu context conflict thì không kết luận vôcăn cứ.
- Câu khôngnêunăm xử lý explicitdefaultseason hoặc clarification; không nhầm năm/đợt/loạiphí/loạiđiểm.
- Khôngworkflowrunningmồcôi sau500/cancel; noanswer đúng lýdo và đầu mối; không cần resetDB/Redis.
- Full82+regressionscritical, HTTP/SSE/providerfail paths có audit/trace; không claim productionready chỉ từ14câu hoặc modeltestOK.

## Artifacts và tác động

Evidence: `backend/storage/admissions_eval415.json` (14câu), `admissions_eval415_audit.json`, `admissions_eval415_scope.json`, `admissions_eval415_schedule_error.json` (service không tái hiện500), `admissions_eval415_schedule_retry.json` (2APIretries). Chỉ nhật ký/memory/WORK_LOG/README được cập nhật. Test tạo recordschat/workflow/usage/keyevents bình thường; không đổi runtime hoặc xóa cache, source/indexpublication/DB/Redis. Không chạy Ruff/Pytest/Vite vì chỉ proposal/read-onlydiagnosis và testAPIthật; không codeimplementation.

## Quyết định và bài học

Ưu tiên hai đợt: A trạngtháicấu hình+ổnđịnhworkflow/route để có nền test tin cậy; B evidence/retrieval/commondecision+nguồnthiếu và full82. Model mới đã gọi được và Gemini fallback hoạt động, nhưng không thể vượt qua gate chỉ chấp nhận bảng hoặc bù context không được retrieve. Không cần đổi embedding/nạp lại toànkho/resetDB để chữa các vấn đề này.
