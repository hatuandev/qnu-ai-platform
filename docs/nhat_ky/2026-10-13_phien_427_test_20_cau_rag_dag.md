# Phiên 427 — Kiểm thử 20 câu đầu với GPT-OSS / Gemma

## Mục tiêu và phạm vi

Người dùng đã đổi model của trợ lý tuyển sinh và yêu cầu bắt đầu lại bộ 82 câu, trước mắt thử 20 câu đầu. Dùng skill chatbot-builder, RAG, ModelOps và clean-code để giữ kiểm thử độc lập và đối soát nguồn; không đổi model, quota, policy, vector, publication hay runtime. Backup vẫn tạm dừng.

Chạy lại harness có sẵn `backend/scripts/evaluate_evidence_417.py` với IDs 1–20 và hai route `dag,rag`. Mỗi route/câu dùng conversation mới, gửi nguyên câu hỏi; đáp án tham chiếu không gửi vào prompt và không nạp vào kho. Các conversations, workflow audit, usage/health phát sinh bình thường từ API test, không phải một phiên hoàn toàn không ghi DB.

- Dữ liệu đầy đủ: [JSON của lượt 20 câu](../../backend/storage/admissions_eval427_first20.json).
- Bộ câu hỏi: [82 câu gốc](../kiem_thu/82_cau_hoi_chatbot_tuyen_sinh.md).
- DOCX gốc kiểm tra SHA-256 khớp fixture: `5bdee19ececf709c472a56459e02a36e7f1afb44ffdba9974f58e899ed66c3fe`.
- Thời gian: 23:48:08–23:49:41 ngày 13/10/2026, UTC+7 (JSON lưu UTC).

## Cấu hình và snapshot

- Primary: `ollama/gpt-oss:120b`; fallback: `ollama/gemma4:31b`; cùng provider `prov_20261013041934` / qnu-9router.
- Temperature 0,2; max_tokens 5000; thinking_budget 0. Không suy ra mọi adapter/provider đã tắt suy luận chỉ từ giá trị UI này.
- Reranker: `prov_rtx5090_vllm` / `bge-reranker-v2-m3`, top_k 5.
- Evidence policy enabled, năm hiện tại theo Asia/Ho_Chi_Minh; ưu tiên TB1906 cho cùng ngữ cảnh năm 2026 giữ nguyên.
- Kho `col_admissions`: epoch 3, 19 binding revisions; vector generation `vg_21324678abcf`.
- Cuối lượt harness xác nhận `configuration_unchanged=true`, `publication_unchanged=true`, `code_unchanged=true` cho danh sách file evidence/workflow mà harness theo dõi; không phải fingerprint toàn repository.
- BE8001/FE3000/9router20128 đều trả HTTP200 khi kiểm tra kết nối. Sandbox chặn socket; đã kiểm tra và chạy benchmark ngoài sandbox đúng phạm vi được cho phép. Không restart dịch vụ.

## Kết quả thực tế

Đã gửi đủ 20 câu × 2 route = 40 lượt. Không đồng nghĩa đã đánh giá được chất lượng 20 câu.

| Kết quả | DAG | RAG trực tiếp |
| --- | --- | --- |
| Trả lời câu 2 | 1 lượt, 14,78 giây | 1 lượt, 9,00 giây |
| Lỗi ưu tiên nguồn câu 1 | HTTP200 nhưng status failed / EVIDENCE_PRECEDENCE_INVALID | HTTP502 / EVIDENCE_PRECEDENCE_INVALID |
| Chặn quota câu 3–20 | 18 lượt HTTP200 / status failed / QUOTA_EXCEEDED | 18 lượt HTTP429 / QUOTA_EXCEEDED |

Tổng: 2 phản hồi answered, 2 lỗi kiểm chứng ưu tiên nguồn, 36 phản hồi chặn hạn mức. Không coi HTTP200 của DAG là thành công nghiệp vụ, và không chấm các phản hồi lỗi quota là sai đáp án tuyển sinh. Harness cũ không dừng khi quota cạn nên các câu sau được gửi nhanh và đều bị chặn. Khi phát hiện đã thử ngắt helper, nhưng lúc đó helper đã hoàn tất cả 40 lượt; không dừng BE/FE/worker/9router.

### Câu 1: Mã trường

Hai route đều báo `EVIDENCE_PRECEDENCE_INVALID`: “Ưu tiên nguồn thiếu trích đoạn đối soát hợp lệ.” Các lần inference đã thành công với GPT-OSS; trace DAG xác định lỗi ở `knowledge_answer`, không phải kết nối /models.

Đọc trực tiếp nguồn đã xuất bản `ks_rev_6280c8de7f46` xác nhận có dòng **“2. Mã cơ sở đào tạo trong tuyển sinh: DQN”**. Vì vậy nguồn có dữ kiện cần thiết; chưa thể kết luận chính xác model đã tạo trường `superseded_by` sai như thế nào vì phản hồi verifier lỗi không được lưu trong report. Code hiện tại yêu cầu quote của nguồn thay thế khớp và source cũ nằm trong rule được phép; nếu không hợp lệ sẽ fail-closed toàn lượt. Cần tái hiện và bổ sung chẩn đoán giới hạn trước sửa, không bỏ kiểm chứng hoặc hardcode DQN.

### Câu 2: Địa chỉ

DAG: “Đối chiếu năm 2026: Địa chỉ Trường Đại học Quy Nhơn: 170 An Dương Vương, P. Quy Nhơn Nam, tỉnh Gia Lai”. RAG trả cùng nội dung. Cả hai trích đúng nguồn “Thông tin TSĐH cập nhật”, trang 1, quote **“3. Địa chỉ: 170 An Dương Vương, P. Quy Nhơn Nam, tỉnh Gia Lai”**.

Đối soát thủ công với đáp án tham chiếu và quote: đúng nội dung trọng tâm. `validate_decision_integrity` đạt 2/2 quyết định supported. Đây không phải điểm Ragas hoặc accuracy của 20 câu.

### Câu 3–20: Chưa đánh giá được nội dung

Hotline, website, chỉ tiêu, số ngành, đối tượng dự tuyển, tuyển thẳng, phương thức, nhiều phương thức, ngành không xét học bạ, ĐGNL sư phạm, GDMN/GDTC, lựa chọn phương thức, ba năm học bạ, lớp tính học bạ, ngưỡng nguồn và điểm sàn: đều bị quota. Câu 3 DAG đã thực hiện một phần inference trước khi bị chặn; không có đáp án hoàn tất để chấm.

## Hạn mức và model thực sự phục vụ

- TenantQuota `tenant_qnu`, tháng `2026-10`: `tokens_used=5.002.480`, `monthly_token_limit=5.000.000`, `is_blocked=false`.
- Đây là giới hạn tháng do app lưu trong PostgreSQL; không có bằng chứng rằng 9router/Ollama hết hạn mức ở nhà cung cấp.
- `DEFAULT_MONTHLY_TOKEN_QUOTA=5_000_000` chỉ tạo quota mới; sửa default không tự thay quota tháng đã tồn tại.
- Lượt benchmark ghi 16 inference thành công, đều provider custom / served model `gpt-oss:120b`, tổng 156.169 prompt+completion tokens; không có fallback sang Gemma. Do quota được kiểm tra trước routing, đổi sang model dự phòng không vượt qua được quota tenant.
- Tổng usage logs tháng: custom 3.361.514 (441 logs), Gemini 379.199 (61), Cloudflare 1.131.098 (336), legacy qnu_workflow 24.226 (97). Tổng tất cả 4.896.037 khác counter quota 5.002.480; chưa xác minh nguyên nhân, không tự tính lại/xóa lịch sử/reset counter. Các logs cũ và các nguồn cập nhật counter cần đối soát riêng.
- Giá cost trong DB là ước tính từ pricing của app, không chứng minh hóa đơn/chi phí thực của model Ollama; không dùng con số USD đó để kết luận model miễn phí hoặc rẻ nhất.
- Hai model chat chung một gateway: có dự phòng model nhưng chưa có độc lập hạ tầng khi gateway ngừng hoạt động.

## Đề xuất tiếp theo (chưa thực hiện)

1. Xin người dùng xác nhận nâng riêng quota `tenant_qnu` tháng 2026-10, đề xuất từ 5 lên 10 triệu để tiếp tục batch 20; giữ counter/lịch sử, không bỏ quota toàn hệ thống. Cần xem mức tiêu thụ sau batch trước cam kết đủ ngân sách cho cả 82.
2. Bổ sung preflight/quota-stop cho harness để không gửi tiếp khi gặp QUOTA_EXCEEDED, TENANT_BLOCKED hoặc dịch vụ mất kết nối; không gộp retries/iterations khác thành accuracy.
3. Tái hiện lỗi precedence với câu mã trường trên cấu hình đã chốt. Xác thực applicability/source identity/exact quote; phân biệt kết luận thay thế thực sự với tham chiếu dư thừa. Giữ fail-closed khi thiếu chứng cứ; đề xuất và được xác nhận phương án trước sửa runtime.
4. Chạy fresh 20 sau khi quota được phép; đối soát số liệu/năm/nguồn/ngữ cảnh và quyết định no-answer. Chỉ mở 62 câu còn lại sau khi đánh giá batch này.

## Tệp thay đổi và kiểm chứng

Chỉ tạo artifact benchmark qua harness có sẵn và nhật ký này; cập nhật `docs/nhat_ky/README.md`, `docs/memory/PROJECT_CONTEXT.md`, `docs/WORK_LOG.md`. Không sửa code ứng dụng hoặc harness.

Kiểm chứng: kết nối HTTP, hash DOCX, manifest snapshot, 40 phản hồi, trace DAG, logs inference, TenantQuota và quote source read-only, integrity 2/2, fingerprints cuối lượt. Không chạy Ruff/Pytest/Vite build vì không đổi mã nguồn; không công bố suite hoặc Ragas đã đạt. Hai truy vấn chẩn đoán tạm ban đầu lỗi kiểu datetime/encoding stdout đã sửa và chạy lại, không phải lỗi runtime của app và không thay đổi DB.

Kết luận: kết nối và model chính hoạt động, nhưng chưa nghiệm thu RAG/DAG với batch 20. Đang chờ quyền điều chỉnh quota; có lỗi precedence cần xử lý sau khi đối soát. Không reset DB, nguồn, vector hay lịch sử để mở khóa kiểm thử.
