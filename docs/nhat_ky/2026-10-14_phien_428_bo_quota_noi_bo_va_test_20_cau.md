# Phiên 428 — Bỏ quota nội bộ, giữ usage và kiểm thử RAG/DAG

## Yêu cầu và quyết định

Người dùng yêu cầu không giới hạn token khi chạy RAG/DAG, thay cho đề xuất nâng lên 10 triệu. Yêu cầu này ưu tiên hơn mặc định quota trong skill ModelOps/chatbot. Dùng các skill backend, ModelOps, clean-code, RAG và chatbot để triển khai sentinel không giới hạn nhưng giữ audit và lỗi nhà cung cấp. Không bỏ guardrails/RBAC, timeout, circuit breaker hay giới hạn độ dài một phản hồi.

Quy ước: **TenantQuota.monthly_token_limit = 0 là không giới hạn**, cost limit 0 cùng ý nghĩa; ProviderApiKey.quota_limit = null là không giới hạn như contract sẵn có. Không giả lập “unlimited” bằng một số token rất lớn. Hạn mức dương được quản trị chủ động cấu hình vẫn có contract kiểm tra, nhưng bản cài đặt này không đặt hạn mức hiện tại hay mặc định tháng mới. Không đổi model/request routing hay chính sách evidence.

## Thay đổi mã nguồn

- `backend/app/core/config.py`: mặc định token/cost quota 0, validation không âm.
- `backend/app/modules/modelops/models.py`: defaults TenantQuota 0/0, không đổi kiểu cột hoặc schema DB.
- `backend/app/modules/modelops/services/usage_accounting_service.py`: chỉ chặn token khi limit dương; giữ TENANT_BLOCKED và usage logging; tạo tháng mới lấy cả token/cost defaults.
- `backend/app/modules/modelops/schemas.py`: mô tả API rõ 0 là không giới hạn, giới hạn không âm.
- `backend/app/modules/modelops/services/provider_service.py`: bỏ các hạn mức token số cứng trong preset/seed key, dùng null; không bỏ phân loại upstream 429/billing/invalid credentials.
- `backend/.env.example`: minh họa quota 0; không thêm hoặc thay đổi khóa LLM trong .env thật.
- `backend/tests/test_unlimited_token_usage.py`: quota 0 trên hơn 5 triệu token; ghi usage, blocked account, DB outage, tháng mới, preset keys, API percent không chia 0, upstream 429/billing/401.
- `backend/tests/test_unlimited_usage_postgres.py`: tạo tháng mới và usage trên DB thật trong outer transaction rollback; chứng minh fixture biến mất sau test.

Không sửa Frontend vì dashboard hiện hiển thị usage độc lập và không render thanh giới hạn tháng; API hiện có đã tính usage_percent 0 khi unlimited. Không migration kiểu cột; defaults là SQLAlchemy/application defaults, không thay server defaults có sẵn ngoài app.

## Cấu hình dữ liệu thật được người dùng cho phép

Read-only kiểm tra trước: tenant `tenant_qnu` tháng `2026-10` chỉ có một quota row; các managed/legacy keys đều đã quota null. Không cần đổi trạng thái/key/counter của provider.

Transaction row-lock exact quota ID `12ba7e16-717c-4016-9388-d104f017a092`, kiểm tra đúng tenant/tháng, chỉ đổi monthly_token_limit 5.000.000 → 0 và monthly_cost_limit_usd 100 → 0. Sau commit đọc lại:

- tokens_used giữ nguyên **5.002.480** tại thời điểm đổi;
- cost_used_usd giữ nguyên **0,8157183** (pricing estimate nội bộ, không phải hóa đơn nhà cung cấp);
- is_blocked vẫn false; không xóa logs hoặc reset bộ đếm.

BE đang chạy GET `/platform/v1alpha1/modelops/quotas/tenant_qnu` trả 0/0, used 5.002.480, percent 0. Live chat sau đó vượt bộ đếm cũ mà không bị QUOTA_EXCEEDED. Dev reload nhận source mới; agent không chủ động stop/restart BE/FE/worker. Worker không được coi đã hot-reload: cần restart worker khi tiếp tục các công việc dùng process lâu sống.

## Kiểm chứng thay đổi quota

- Trước sửa: regression có **2 fail / 6 pass**, tái hiện limit0 vẫn bị QUOTA_EXCEEDED và defaults vẫn 5 triệu/100USD.
- Focused ModelOps/usage/key rotation: **55 pass**, gồm 8 regression đầu và 47 ca liên quan.
- Sau bổ sung API/preset + PostgreSQL thật: **11 pass** (10 unit, 1 PostgreSQL rollback opt-in).
- Ruff toàn Backend đạt, có cảnh báo không đọc được một số thư mục storage/pytest cũ.
- Full Backend: **1158 pass / 11 baseline fail / 13 skip**, 182,37 giây; log `backend/storage/pytest428_full.log`. 11 fail đúng danh sách baseline phiên 426: consulting export (2), publishing/GC/canary (6), reconciliation (1), auth session cookie (1), universal tools (1). Không công bố full suite xanh. PostgreSQL test opt-in đã chạy riêng, skip trong full suite không phủ nhận kết quả riêng.
- Không Vite/Biome vì không đổi FE. Không chạy Ragas.

## Lượt 20 câu mới

Chạy `scripts.evaluate_evidence_417` có sẵn, IDs 1–20, hai route dag/rag, conversation độc lập, expected answers chỉ ở report, không đưa vào prompt hoặc kho. Artifact riêng: [admissions_eval428_first20.json](../../backend/storage/admissions_eval428_first20.json). Không gộp với lượt 427 bị quota.

Đã hoàn tất 00:01:48–00:12:52 ngày 14/10/2026: 40 lượt, **0 quota errors**. DAG10answered/10insufficient; RAG8answered/11insufficient/1HTTP502 EVIDENCE_PRECEDENCE_INVALID (câu1). Decision18supported/5partial/16missing/1error; integrity23/23 không thay thế kiểm tra ngữ nghĩa. 120 inference logs cùng conversation, tất cả custom/gpt-oss:120b,1.130.701tokens,noFallback; Gemma chưa được kiểm chứng. Trung vị DAG16,48s/RAG13,28s, cao nhất34,78s/32,16s. Config/publication/evidencecode tracked không đổi cuối lượt.

Đối soát cuối DB: used **6.199.933**, limits **0/0**, is_blocked=false. Counter tiếp tục tăng, không reset; tổng logs conversation benchmark không tự bằng toàn traffic của tenant. [Báo cáo đối soát 20 câu](../kiem_thu/2026-10-14_20_cau_rag_dag_gpt_oss.md). Câu2 địa chỉ,11 học bạ sư phạm,17 ba năm học bạ trả đúng trọng tâm; câu5 chỉ DAG trả5173. Câu9 cả2 trả sai/thiếu chỉ4PT mặc dù source cóPT5/405+tuyển thẳng301, vẫn supported; câu14/15 missing doquote/entity binding,13nhầm trườngđích/organizer,16đổi ý nghĩa lựa chọn thành kết hợp. Có partialfooter gây mâu thuẫn ở3/12. Đây là danh sách đề xuất sửa RAG/DAG, chưa tự sửa hoặc nghiệm thu accuracy/Ragas.

## Giới hạn và công việc tiếp theo

Giữ max_tokens=5000 của trợ lý và các ngân sách riêng của bước xử lý, không hiểu “bỏ quota tháng” là sinh token vô hạn mỗi request. Lỗi billing/rate limit nhà cung cấp vẫn có thể chặn hoặc kích hoạt fallback; hai model cùng gateway chưa tạo dự phòng hạ tầng độc lập. Quota counter cũ khác tổng logs chưa được sửa/reset để che mất chênh lệch.

Không reset DB, không OCR/reembed/publish, không đổi model hoặc nguồn TB1906, không bật backup, không nâng cấp dependencies. Lỗi evidence cần đề xuất riêng và test tái hiện trước triển khai, không hardcode đáp án hoặc hạ guardrails để làm benchmark xanh.
