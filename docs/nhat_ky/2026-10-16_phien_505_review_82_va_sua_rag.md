# Phiên505 — Review 82 câu và sửa các lỗi có bằng chứng

Ngày 2026-10-16. Người dùng yêu cầu đọc lượt 82 câu mới nhất, tìm nguyên nhân và sửa.
Không chạy lại 82 câu, không đổi Top K/model/nguồn/vector/config, restart hoặc Git.

## Đối chiếu báo cáo, không lấy nhãn cũ làm kết luận

Artifact đầu vào: `backend/storage/eval498_configured_20-20-30-5/` gồm bốn JSON,
nhãn và REPORT. Báo cáo ghi 27 PASS / 7 PARTIAL / 24 FAIL / 24 ERROR. Đây là nhãn
của lượt đã chạy, không phải chất lượng sau bản sửa505 hoặc nhãn đã được duyệt độc lập.

- Có đúng 82 ID riêng. Trong 7 lỗi hợp đồng: 5 lỗi root wrapper `$`, một lỗi trường
  `missing_constraints` sai cấp và một lỗi chọn 5 passage IDs vượt trần4; không thể
  gọi cả7 là schema echo. Các lỗi đó có `code` và `validation_errors` khác nhau.
- Q23 gửi thực tế chỉ hỏi định nghĩa PT1, không có năm2026 hoặc history. Section
  của fixture không được gửi vào chat. Vì vậy nhãn FAIL chỉ vì nguồn2024 chưa đủ
  căn cứ; cần chấm lại phạm vi câu hỏi, không ép năm2026 vào runtime để khớp gold.
- Q18/30/57/62 có retrieval trước khi về mẫu từ chối, không phải chưa truy xuất.
  Reranker có thể lọc hết candidates; `attach_diagnostics` mặc định false làm báo
  cáo nhầm. Chỉ Q18 được kiểm chứng live lại trong phiên này.
- Trace đầu vào đã có `section_candidates`, compact payload và whole-group repack
  của502. Dòng mô tả backend chỉ494/495 không đủ làm bằng chứng phiên bản runtime.
  Fingerprint runner cũ cũng không bao phủ mọi file (ví dụ prose_fallback).
- Báo cáo17 overflow là số quan sát của lượt cũ. 36.000 ký tự không đồng nghĩa
  một lượng token cố định; phải tính cả instruction/metadata/output. Không sửa
  bằng tắt kiểm chứng hoặc tự giảm cấu hình của người dùng.
- Q2 verifier dùng kiến thức ghi nhớ để bác địa chỉ nguyên văn. Q3 tự thêm yêu
  cầu năm hiện tại/độc quyền hotline dù câu hỏi không yêu cầu. Q5/Q43 có trường
  `topic_coverage` bị bỏ trống mà hợp đồng vẫn hợp lệ, rồi bị gate coverage chặn.

## Thay đổi có phạm vi

1. `evidence_contracts.py`: unwrap một envelope chỉ có `$` object, không merge,
   không di chuyển trường lồng, không điền verdict. Tiếp tục Pydantic strict và
   exact IDs. Khi có topics, yêu cầu đủ/đúng khóa coverage và đánh giá true/false.
2. `evidence_model.py`: chỉ dẫn root rõ hơn, sửa đúng giới hạn/hierarchy trong
   lượt repair có sẵn; phân biệt error_kind khi JSON sai cú pháp. Không thêm retry
   hoặc tự hợp thức hóa mệnh đề. Verifier không dùng training knowledge bác nguồn.
3. `evidence_context.py`, `evidence_verification.py`, `evidence_indexed_audit.py`:
   compact-mode giữ quote/semantic scope một lần trong reference_catalog. Dedup
   theo toàn identity trước khi bỏ hash/span vận chuyển khỏi prompt. Raw bound
   claims và citations không bị sửa. Không cắt bằng chứng hoặc giả phép đo token.
4. `evidence_passages.py`: selector tối đa12 IDs, tách thành nhóm cùng nguồn tối đa4
   references/claim. Giữ mọi passage đã chọn, bind/verify từng claim. Không gộp số
   khác năm/nguồn và không tăng reference limit của hợp đồng EvidenceClaim.
5. `prose_fallback.py`: nếu CE lọc hết, giữ candidate lexical có giới hạn để kiểm
   chứng độc lập (không giả điểm). years=[] được ghi rõ là không có hạn chế năm;
   không phát sinh cấm mọi nguồn có niên vụ. Năm tường minh giữ nguyên. Bổ sung
   trace verifier_complete/topic_coverage/audit_complete, không log raw proof.
6. `service.py`: nhánh hybrid rỗng thử canonical recovery cùng snapshot trước khi
   từ chối. Ghi retrieval_executed thật. Không override conflict hoặc fact/table
   đã được chứng minh; provider errors tiếp tục là lỗi.
7. `citation_guard.py`: bỏ mẫu từ chối chèn hotline/email/khẳng định kho không có.
   Mẫu mới nói rõ chưa xác minh được, không biến failed retrieval thành dữ kiện.

## Kiểm chứng và kết quả thật

- Regression trước sửa: 8 FAIL / 4 PASS, tái hiện root wrapper, empty CE, empty
  hybrid và mẫu từ chối không an toàn. Sau batch trung gian:124 PASS.
- Scoped sau sửa hợp đồng:124 PASS (5,16s); bộ mở rộng có1 assertion cũ đòi hotline
  cố định thất bại,142 PASS. Sau cập nhật các expectation không còn phù hợp và mock
  recovery mới, final targeted25 PASS (5,18s). Không cộng các tập test giao nhau.
- Ruff toàn phạm vi505 PASS, exit0. Kiểm tra UTF-8/noBOM/LF/newlinks/diff PASS.
- Full đầu:1860 PASS/16 FAIL/17 SKIP (211,71s), exit1. Ngoài11baseline:3assertion
  cũ đòi hotline,1assertion template riêng từng domain,1mock follow-up chưa cô lập
  recovery mới. Chỉ cập nhật kỳ vọng hợp đồng đã đổi/mocks, không hạ guard nguồn.
- Full cuối `storage/review505-verified.xml`: **1866 PASS/11 FAIL/17 SKIP**,
  196,61s, exit1. Exact11 test IDs trùng `prose502-verified.xml`,0new failures;
  **tổng suite vẫn FAIL**, không gọi toàn backend PASS. Đây là full chạy lại sau
  failure có nguyên nhân, không chạy full sau từng thay đổi nhỏ.
- Probe dùng lại `scripts/probe_prose_502.py`, wrapper
  `scripts/probe_review_505.py --live --ids ...`; nội bộ duy nhất, không cloud,
  cache bypass trong process, không flush hoặc sửa cấu hình. Snapshot
  `b7456674dcc9b51ce736`, assistant revision không đổi qua các batch đã hoàn tất.
- Giữ mọi kết quả trung gian ở storage, không chọn chỉ lượt đẹp:
  `review505-live.json`:6 lượt, Q18 answered; Q2 lỗi JSON audit; Q9 lỗi5IDs;
  Q5/Q3/Q34 chưa đủ kiểm chứng. Có probe Q43 trước đó: không overflow nhưng thiếu
  topic coverage. Một lần sandbox chặn mạng trả ALL_PROVIDERS_UNAVAILABLE;
  lần có quyền mạng mới đo được dense/reranker thật, không gộp hai kết quả.
- `review505-live-final.json`: Q9 answered PT1–PT5 năm2026 + xét tuyển thẳng,
  7citations; Q5 answered cập nhật5.173 và phân biệt4.500 cũ,2citations;
  Q43 answered KV1=0,75,3citations; Q3 vẫn từ chối do tự áp cấm historical.
- `review505-scope-final.json`: sau làm rõ seasonless scope, Q3 answered hotline
  có2citations (còn dài/lặp và thêm website); Q2 lỗi provider nội bộ, không chuyển
  cloud. Không coi answered/citation là điểm accuracy hay nghiệm thu mọi82câu.
- Post-read config hash `4811e541…261e` và snapshot trùng lượt82. Các probe đầu ghi
  snapshot/revision trước/sau; wrapper nay ghi thêm hash config thực, không chỉ dựa
  updated_at. Chưa suy fingerprint bao phủ code từ report runner cũ.

Lệnh chạy tại `backend`: `.venv/Scripts/python.exe -m pytest` với các test phạm vi
đã nêu, full `-q --junitxml=storage/review505-verified.xml
--basetemp=storage/review505-verified-temp`; Ruff `-m ruff check` trên các file RAG,
harness và tests505 liên quan (không fix toàn repo). Probe `-m scripts.probe_review_505
--live --ids 2 18 9 5 3 34`, rồi `--ids 9 5 43 3`, cuối `--ids 3 2`, mỗi chặng lưu
artifact khác tên. Không gửi expected_answer, không runner retry, giữ cả lỗi trung gian.

## Giới hạn còn lại

- Chưa sửa/đo lại toàn bộ12 visible-audit rejection,4 numeric, toàn bộ bảng/fact,
 7citation thiếu hash/span hoặc7partial. Không lấy gold cũ thay nguồn đang xuất bản.
- Q2 chưa nghiệm thu do lỗi model/provider ở các lượt thử. Q34 ở batch trung gian
  còn refusal; chưa có probe cuối. JSON đặt trường sai cấp vẫn phải repair/fail;
  không di chuyển trường hoặc tự điền true để chạy qua.
- Provider vẫn có thể lỗi; chưa có tokenizer/window đáng tin cho toàn bộ runtime.
  Compact prompt không bảo đảm mọi input vừa8k. Whole-group repack502 giữ nguyên.
- Recovery thêm các lượt đối soát cho câu trước đây trả template0call; latency có
  thể tăng. Candidate rỗng vẫn có thể kết thúc thiếu căn cứ sau timeout/binding
  hoặc semantic rejection; không đánh đồng canonical fallback với câu trả lời chắc đúng.
- Không thay dữ liệu, reindex, publish, migration, restart/deploy, commit/push;
  không sửa11baseline ngoài phạm vi. Chưa kiểm tra WebUI/82 lại sau sửa.
