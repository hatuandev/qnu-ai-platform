# Phiên 765 — F15: giữ relevance và đọc đúng ngoại lệ, kiểm tra một lần

Ngày 2026-10-31. User yêu cầu tìm nguyên nhân F15 bị từ chối, sửa và test không retry để làm xanh. Giữ nguyên các diff của phiên764; không đổi provider, quota, source, index, publication hoặc checkpoint và không restart dịch vụ đang chạy.

## Chẩn đoán từ lượt lỗi, không gọi lại model để dò đáp án

- Đọc report764 và xác thực actor/workspace/collection trước khi đọc chunk và bundle đang phục vụ. Đối chiếu block nguồn trang8 qua bundle đã kiểm hash.
- F15 cũ trả JSON abstain với12completion token, input18526; không có lỗi context/output/transport. Đoạn điều kiện riêng có trong rerank hạng4.
- `sources_for` đã bỏ thứ hạng retrieval để sort theo document/page/path. Kết quả15table đứng trước5paragraph; điều kiện riêng từhạng4 xuốngE18, đoạn quy định chung xuất hiện cảE17/E20. Đây là lỗi trình bày relevance quan sát được, không phải thiếu nguồn.
- Promptv4 yêu cầu tránh mâu thuẫn nhưng chưa phân biệt quy định chung với ngoại lệ có scope rõ. Nguồn chứa cả hai; không nên mặc định chúng là số liệu xung đột. Model không trả lý do nội bộ cho abstain, nên không khẳng định duy nhất một yếu tố gây từ chối.

## Sửa tổng quát

- `answer/drafting.py::sources_for` giữ thứ tự relevance đã được retrieval/rerank xác định. Citation/structure giữ nguyên, không dùng thứ tự trang làm độ ưu tiên hay suy liên kết bảng.
- Promptv5: so đối tượng/phương thức/thời gian/điều kiện trước khi kết luận mâu thuẫn; áp dụng trường hợp riêng chỉ khi nguồn xác lập rõ. Giữ quan hệ và/hoặc, đơn vị/ngưỡng và citation. Unknown hoặc xung đột chưa giải vẫn abstain.
- Không thêm tên ngành, số điểm, từ khóa F15 hoặc expected answer vào prompt; không thay dữ kiện đã xuất bản.
- Unit765 tái hiện RED việc nguồn liên quan ở trang sau bị đẩy xuống; sau sửa PASS. Cập nhật testversion764/API648 để kiểm hợp đồngv5.

## Live kiểm tra một lần

- Một lượt API hiện tại,19câu cũ không được chạy lại toàn bộ. Chọn trước5case: F15,F14,F17,F18,F19. Mỗi câu một hội thoại mới và một POST, không retry theo kết quả. Script local có thư mục `tmp/f15-once-765` tạo độc quyền, không cho chạy lại để chọn kết quả.
- Trước inference kiểm ModelOps max_key_attempts1 và không fallbackanswer. F15 có đúng1execution observation attempt1/codeok.
- **F15 PASS ở lần duy nhất,18.19s**, promptv5, input18668/completion178/total18846. Trả đúng điều kiện riêng và hai ngưỡng bổ sung; citationE4 tới chunk đã published ở trang8. Đã đối chiếu quan hệ điều kiện với block nguồn.
- Danh sách rerank IDs và indexmanifest giữ nguyên so với F15 lỗi764; chatprovider/capacity/top20/candidate50 không đổi. Chỉ hợp đồng prompt và thứ tự evidence thay đổi.
- F14 và3negative F17–F19 cũngPASS,5/5 tổng76.37s. Không suy thành19/19PASS cùngv5; những câu còn lại NOT_RUN trong phiên này. Nhãn benchmark vẫn draft/semantic_reviewNOT_RUN.
- Report `tmp/f15-once-765/admissions-answers.json`; kết quả lỗi764 được giữ nguyên trong report cũ.

## Regression và giới hạn

- Focused: test_answer_evidence_order765 +test_answer_projection764:5PASS,exit0. Ruff scopedPASS.
- Full unit:533PASS/1FAIL,exit1,34.43s. Lỗi nền đúngID `test_source_purge_716.py::test_accept_rechecks_publication_after_preview_before_preparing_purge`,invalid_identity tạiworkspaces/access.py39. Không sửa ngoài phạm vi.
- API integration648: `scripts/run_isolated_tests.py tests/integration/test_answers_api_648.py -q --tb=short`, cwdbackendV1,21PASS/exit0/195.80s. Databasecôlập `qnu_v1_test_fb6ee61618c9455b` đãdrop,legacy_sentinel preserved;harness205.42s. Log `tmp/integration-765.txt`.
- Không đổi frontend nên không chạy lại build/FEtests của764. Không gọi lại F15 sau khi đã nhận kết quả, không gộp kết quả qua cấu hình khác để báo tỷ lệ.

## Bàn giao

Đã xử lý lỗi relevance và quy tắc đọc ngoại lệ; F15 đạt một lần có audit. Muốn chạy CLI bằng mã mới cần mở lại serve; không cleanup/init hay upload/OCR/compiler/publish lại. Một lần đạt chưa chứng minh tỷ lệ ổn định trên mọi cách hỏi; giữ report để so thí nghiệm độc lập sau này.
