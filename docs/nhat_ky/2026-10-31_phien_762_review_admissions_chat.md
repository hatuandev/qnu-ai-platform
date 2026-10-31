# Phiên 762 — Review kết quả admissions-chat và các giới hạn token

Ngày 2026-10-31. Người dùng đã triển khai tiếp ở IDE khác, gửi ảnh báo cáo phiên761 và yêu cầu review, giải thích lỗi giới hạn token. Chỉ review mã/kết quả hiện tại; không sửa logic, cấu hình DB, checkpoint hoặc restart dịch vụ trong lượt review này. Giữ mọi thay đổi chưa commit.

## Bằng chứng hiện tại

- Report `tmp/v1-e2e/1da945adac7c/runs/admissions-chat-1793437469376204800/admissions-answers.json`: expected19/passed19/failed0/not_run0. Playwright results.json: expected1/unexpected0/flaky0, duration224547.549ms.
- Đây là kết quả tích lũy: F01–F11 có answer ID đã xuất hiện trong report trước; F01–F03 dùng top_k10/candidate_k30, F04–F08 dùng20/30, F09–F19 dùng20/50. Không chứng minh19 câu inference mới cùng cấu hình trong3.7phút.
- Checkpoint queryHistory có11 mục ởF01/F04/F09/F12, trong đó8 mục model_abstained,2turn_creation_failed,1rerank_input_limit_exceeded; không suy tất cả là retry của lần chạy cuối.
- Nhãn vẫn `draft_agent_read_pdf_not_human_approved`, semantic_reviewNOT_RUN. Prompt token quan sát12483–41835/câu; không đồng nghĩa chạm context128K.

## Finding

1. P1 — `admissions-chat.ts:158`: dùng nhãn expected_numbers/patterns/pages quyết định sinh lại tới5lần, báo cáo cuối chỉ giữ kết quả được chọn. PASS sau chọn đáp án không đo độ đúng lần đầu; rerun còn reset completed sai ngay cả khi recoveryCount đã hết. Cần tách nghiệm thu một lần với phục hồi chủ đích, báo mọi attempt/config.
2. P1 — `admissions-chat.ts:110`: query có conversation nhưng thiếu turn ID bị mặc định coi failed rồi tạo hội thoại mới. Trạng thái này cũng xảy ra khi HTTP trả lỗi sau lúc server đã nhận; chưa đọc turns để loại running/uncertain. Có thể sinh request trùng. Cần reconcile trạng thái trước, không đổi khóa để vượt idempotency.
3. P1 — `drafting.py:25`: chỉ dẫn toàn cục nêu ngành của benchmark và yêu cầu kết hợp ô nối trang nhưng chưa bắt buộc chứng cứ liên kết bảng/hàng. Ô đầu rỗng không chứng minh cùng thực thể. Cần quy tắc cấu trúc tổng quát, proof/citation và negative case bảng gần nhau không liên quan.
4. P2 — `drafting.py:12`: system prompt đổi nhưng PROMPT_VERSION vẫnv3; báo cáo trộn turn cũ/mới cùng phiên bản. Cần version/hash prompt và cấu hình bất biến trong benchmark.
5. P2 — `admissions-chat.ts:279`: nuốt lỗi cập nhật assistant rồi tiếp tục, nên có thể dùng cấu hình cũ khi409revision conflict/403/5xx. Cần trả lỗi và xác minh cấu hình đọc lại.

## Giới hạn token

- Rerank409: profile cũ ghi input1024 dù server báo context8192; code dùng byteUTF8 làm cận trên bảo thủ, không phải token đo thực. Bỏ profile override là đúng.
- Chat422truncated: output request và reasoning chung ngân sách sinh, độc lập context lớn; thêm taskanswer qua policyverified là hướng đúng, không bảo đảm mọi request không bao giờ hết output.
- Quota429: tổng tháng và đặt chỗ khác context/output từng request. Nâng allowance E2E không tối ưu request; reservation unknown cần reconcile có chứng cứ.
- candidate_k/top_k là số ứng viên/ngữ cảnh, không phải token. Tăng giúp recall nhưng tăng input. messages_for hiện gửi cảtext vàstructure nên bảng có phần nội dung lặp.

## Kiểm chứng review thực chạy

- BackendV1: `.venv/Scripts/python.exe -X utf8 -m pytest tests/unit/test_modelops_reasoning_746.py -q --basetemp ../tmp/pytest-review-762 --tb=short`: exit0,16PASS.
- FrontendV1: Vitest e2e-capacity735 +e2e-provider-selection: exit0,14PASS.
- FrontendV1: `npm run test:e2e:typecheck`: exit0.
- BackendV1 Ruff trên reasoning.py,answer/drafting.py,answer/service.py,test_modelops_reasoning746: exit0.
- Git diff --check phạm vi review: exit0.
- Không chạy model/E2E mới trong lượt review. Full suiteNOT_RUN; lỗi nền source_purge716 từ phiên760 vẫn là kết quả lịch sử, chưa xác minh lại. Không kết luận toàn chức năng đã xử lý triệt để.
