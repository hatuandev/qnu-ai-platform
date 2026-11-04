# 26 — Trợ lý và hội thoại backendV1

Phạm vi `backendV1/`, tiếp sau [hỏi đáp có nguồn](25_hoi_dap_co_trich_dan_backendv1.md).
Không thay schema/quyền/backend cũ. Workspace là biên giới quyền riêng của v1.

1. Admin tạo trợ lý với collection, persona giọng văn, ModelOps chat provider/default,
   topK/history/output budget. Provider phải được cấp. Không seed hoặc sao chép key.
2. Actor mở hội thoại của chính mình, ghim assistant revision/config và document
   scope. Owner lấy từ xác thực; không nhận history/owner/system prompt từ client.
3. Gửi turn với key và expected_turn_no. BE lưu request/sequence/lease trước HTTP;
   một lượt running, replay không gọi model lại, khác body/sequence báo conflict.
4. Mọi lượt mới gọi model qua ModelOps để phân loại và làm rõ chủ thể trong một
   request. Lời chào/cảm ơn/giới thiệu được model tự viết theo tên và persona,
   lưu `direct_reply`. Câu dữ kiện trả `knowledge` và chưa có câu trả lời.
   History chỉ gồm câu hỏi nghiệp vụ đã hoàn tất, không dùng assistant text làm
   dữ kiện. Lưu câu hỏi gốc, resolved query, route và usage trong `rewrite_trace`.
   Khi history rỗng, dùng nguyên câu hỏi gốc để truy xuất. Model vẫn phân loại lượt.
5. Với knowledge, search/retrieval/answer dùng pipeline648, citation và kiểm nguồn hiện hành.
   Kiểm lại owner/quyền/assistant revision/active/lease trước và sau gọi model.
6. Lưu cặp question/result/citation hoặc status/error. Lỗi provider vẫn báo lỗi
   thật. GET history kiểm nguồn, ẩn result/source cũ không hợp lệ, giữ history row.

Đổi config assistant tăng revision và cần chat mới; collection/document scope
không tự thay trong hội thoại. Owner có thể đổi title/archive, archive chặn send.
Khi admin tắt trợ lý hoặc owner archive hội thoại qua API cập nhật, BE hủy bền
vững các lượt đang chạy trong đúng phạm vi cùng transaction trạng thái/audit.
Bật/mở lại chỉ cho phép lượt mới, không nhận phản hồi muộn hoặc chạy lại lượt
đã hủy. Lịch sử completed giữ nguyên; key cũ báo cancelled, lượt mới dùng key mới
và sequence hiện hành. Chỉ bật/tắt không đổi revision cấu hình trợ lý.
Hết lease chuyển uncertain khi đọc turns/gửi tiếp, không tự retry hoặc chạy job.
LLM trả muộn không được ghi completed qua checkpoint đã hết quyền.

Migration0010 tạo3bảng chat_* khác tên legacy và downgrade từ chối giữ evidence.
Chỉ migrate DB thử; chưa config/start/restart/deploy phục vụ hoặc publish/index corpus.

Live hai lượt trên PDF tổng hợp/ModelOps BGE-M3+Qwen/Qdrant PASS chức năng: history2,
replay cùng usageID, source đúngrevision; OCR/Compiler mock. Có lỗi schema/abstain
ở lượt trước và một diễn giải ghi chú chưa đủ căn cứ trong output live cuối;
chưa quality benchmark hoặc semantic verifier.

[API/vận hành](../../backendV1/docs/assistants-conversations.md) ·
[Báo cáo649](../bao_cao/context649/REVIEW.md).
