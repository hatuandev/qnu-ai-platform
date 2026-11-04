# Phiên861 — Phạm vi đọc và độ bao quát RAG

## Yêu cầu và phạm vi

Ưu tiên sửa RAG; xây cơ chế chung xác định phần cần đọc, phần đã trả lời và phần
còn thiếu. Giữ policy/model/snapshot hiện có và các thay đổi chưa commit của người
dùng. Không reset, restart, reindex, biên soạn lại, xuất bản hoặc push Git.

Áp dụng skill RAG pipeline/evaluation, clean code, backend và frontend. Không tạo
agent phụ. Đây là heuristic cấu trúc + hợp đồng model, chưa phải bảo đảm mọi câu
trả lời hoàn chỉnh hoặc đúng ngữ nghĩa.

## Thay đổi

- `answer/structure_context.py`: nhóm điều/mục hoặc danh sách có dẫn nhập từ
  canonical source; không phụ thuộc ranh giới phần Compiler. Kiểm cùng input,
  OCR run, revision và hash. Không ghép nguồn khác hoặc sửa raw OCR.
- `answer/context.py`: expansion có scope/manifest và ngân sách; ghi rõ phần
  không lấy được do budget/scope/không có chunk. Bộ đệm bundle chỉ sống một request.
- `answer/coverage.py`, schemas/drafting/cells/service: `answer_plan`, `assessment`,
  `coverage`; prompt `qnu.rag.answer/v17`. Kiểm EID, đơn vị cấu trúc được dẫn và phần
  chưa được cung cấp; giữ các witness trong nguồn response cho kiểm lại lịch sử.
- UI hội thoại: báo câu trả lời partial, yêu cầu chưa giải đáp và mở đúng nhóm
  nguồn chưa được dẫn. Không gắn nhãn verified cho kết quả chỉ kiểm ID.
- Regression mới861 và cập nhật assertion phiên bản/schema trong các test liên quan.

## Kiểm chứng đã chạy

- Targeted backend cuối: **44 PASS**, gồm unit và handler/API với DB/Qdrant/blob
  cô lập, kiểm foreign evidence, cùng phạm vi, thiếu phần, source closure của
  abstain/partial; một request model giả cho mỗi case. DB
  `qnu_v1_test_e800ff7e75514cf6` đã dọn, sentinel legacy giữ nguyên.
- Targeted frontend cuối: **5 PASS**; kiểm nội dung thiếu và chọn đúng tập nguồn.
- Full frontend sau khi thêm nút mở nguồn: **773 PASS** trên 93 tệp qua
  `npm exec -- vitest run --maxWorkers=2`. Build và Biome đạt sau khi chỉnh nhãn
  ngăn dẫn nguồn để phân biệt phần cần đối chiếu.
- Recovery666 chạy riêng do yêu cầu event loop Windows: **4 PASS**.
- Full backend đầu bị chủ động dừng để bổ sung source closure trước gate cuối;
  không coi là PASS. DB `qnu_v1_test_02a2395405b44ddb` đã dọn, sentinel giữ nguyên.
- Lần focused rộng trước đó:101 PASS/1 FAIL do fixture giả thiếu workspace/collection
  trên IndexRun; đã sửa fixture và kiểm lại riêng, không hạ guard ứng dụng.

## Qwen thật — không retry làm xanh

Đọc cùng snapshot published/index có sẵn của ứng dụng, reasoning off, không thay
cấu hình và không tạo hội thoại. Mỗi case một request model; token ghi qua ModelOps.
Năm case gồm hai câu gốc đang gặp vấn đề, hai cách hỏi lại độc lập và một câu ngoài
phạm vi nguồn. Không phải toàn bộ19/53câu hoặc benchmark độc lập đa tài liệu.

- Cohort v16:4/5 đạt rubric ban đầu. Một cách hỏi thiếu hồ sơ; đã sửa ưu tiên nhóm
  điều thay vì danh sách hẹp xếp hạng cao và cập nhật prompt lênv17.
- Cohort v17: rubric tự động ban đầu3/5. Audit phát hiện một false negative do
  khác vị trí dấu tiếng Việt trong từ chỉ sức khỏe; giữ nguyên báo cáo đầu, không
  gọi model lại để sửa điểm. Đọc đáp án thực tế:4/5 đủ tiêu chí nội dung.
- Câu gốc về điều kiện dự tuyển vẫn chỉ nêu điều kiện chung, chưa nêu nhóm bằng
  cấp/đối tượng. **Không tuyên bố đã sửa hết**: coverage phát hiện `partial`, chỉ rõ
  nhóm đối tượng chưa được trả lời và giữ các nguồn chưa được dẫn để đối chiếu.
- Hai câu hồ sơ đã trả quy định chung, báo thiếu danh sách giấy tờ chi tiết;
  câu hỏi học phí ngoài nguồn từ chối đúng. Cách hỏi rõ đối tượng + điều kiện trả
  đủ nội dung, bảy unit của nhóm nguồn có citation.
- Thời gian mỗi answer v17:10,05–17,41giây, chưa gồm router hội thoại; không thể
  coi đây là tốc độ end-to-end của UI. Không tự bật verifier hoặc thêm lượt model.

Báo cáo riêng tư ở `tmp/context861/`: `live-initial-v16.json`,
`live-v17-first-attempt.json`, `live-v17-audit.json`. Không đưa corpus vào Git.

## Gate cuối

- Ruff, Biome, frontend build và `git diff --check` đạt. Backend trọng tâm chạy
  qua `backendV1/scripts/run_isolated_tests.py` từ root repo. Full backend dùng
  `scripts.test_database` chia bốn nhóm, Recovery666 chạy riêng trên Windows.
- Full backend chưa đạt nghiệm thu. Một nhóm trả **107 PASS/1 FAIL** tại
  `test_chat_shared_admission_751.py::test_real_redis_enforces_shared_limit_and_releases_own_leases`
  vì môi trường kiểm thử thiếu tiền tố Redis cô lập. Chạy riêng ca này cùng
  các unit coverage861 với tiền tố test đúng cho **20 PASS**. Ba nhóm full còn
  lại bị ngắt trước khi ghi kết quả cuối. Đã kiểm sentinel và dọn đúng ba DB
  test do lần chạy này tạo. Giữ log và receipt trong thư mục kiểm thử cục bộ.

## Giới hạn và bước tiếp

Độ phủ citation không chứng minh model diễn giải đủ từng ý. Nhận diện điều/mục
hiện dùng cấu trúc đánh số và title overlap; chưa bao quát mọi định dạng, toàn bộ
collection hay mọi phụ thuộc điều khoản được viện dẫn. Chỉ báo đủ trong phạm vi
đã đọc; không nới scope/budget hoặc sửa assertion để che thiếu sót.

Sau khi người dùng khởi động lại `make dev`, hội thoại dùng backend mới; không
cần cleanup/init, compiler hoặc reindex chỉ để nhận thay đổi này. Hội thoại cũ
không được ghi đè đáp án lịch sử; thử bằng một lượt hỏi mới.
