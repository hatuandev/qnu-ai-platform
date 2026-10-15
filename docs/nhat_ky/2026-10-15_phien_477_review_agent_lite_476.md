# Phiên477 — Review độc lập báo cáo agent-lite476

## Phạm vi

Người dùng gửi báo cáo476 để xem lại. Chỉ đọc mã, tests và reports; dùng skills clean-code/RAG/Backend, không sửa runtime hoặc chạy model/DB. Không reset, nạp vector, restart, commit/push. Không chạy lại full suite; số1507pass/11fail là báo cáo476, không phải kết quả chạy mới ở477.

## Phát hiện

1. `conversation_acts.resolve_act_scopes` bắt cả AppException từ structured_call và trả scopes unknown. Lỗi provider/JSON/hạ tầng có thể bị che thành câu trả lời answered hoặc NO_MATCHING_RECORDS ở filter. Test `test_scope_fallback_keeps_years_unknown_on_model_error` hiện chủ động chấp nhận hành vi này, trái yêu cầu giữ lỗi dịch vụ.
2. `_handle_act` tải records theo môn của antecedent nhưng không áp dụng explicit years của antecedent trước summarize/render_compact. `validated_scopes` không lọc năm (renderer enumeration mới là nơi lọc). Do đó hỏi riêng2025 rồi yêu cầu giải thích/rút gọn có thể đưa cả2026/unknown vào, dù phần dẫn ghi đúng câu hỏi2025. Cần tái dựng toàn scope chứ không chỉ subject và lời dẫn.
3. `render_compact` group key=(year,code,name), không có source discriminator cho yearNone. Probe thuần bộ nhớ với2nguồn unknown-year cùng mã+tên được gộp thành1dòng. Trái cam kết không gộp chéo unknown-year. Không gọi model hoặc DB trong tái hiện.
4. Handler trảNone (cả lỗi không phải AppException) rồi `RagService.ask` chạy `_ask` với effective.question đã thay thành antecedent. Explain/reformat/filter không xử lý được có thể lặp bảng cũ; filter có thể mất điều kiện năm hiện tại. Tests hiện xác nhận fallback này, chưa chứng minh yêu cầu clarify được đáp ứng.

## An toàn và giới hạn

Report `probe_conversation_acts_second.json` ghi3blocked_destinations cloudflare; không kết luận riêng chữ403 là có/không lộ nội dung. Harness cuối patch4factory aliases nhưng chưa có kiểm thử độc lập phủ mọi đường transport/redirect. Cần kiểm tra nhật ký các lần trước và bảo đảm egress fail-closed trước probe thật tiếp; không đổi cấu hình provider production. Phiên477 không gửi tài liệu đi đâu.

Đã có tiến bộ ở happy-path explain/filter/reformat, chưa nghiệm thu toàn bộ agent-lite. Cần fix4biên và regression tích hợp câu riêng2025→rút gọn, modeldown→error, unknown2sources→giữ riêng, handler bất định→clarify không đổ bảng. User chưa yêu cầu sửa runtime trong lượt review này.
