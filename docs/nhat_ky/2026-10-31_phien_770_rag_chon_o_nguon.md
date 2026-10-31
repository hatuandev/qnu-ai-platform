# Phiên770 — RAG chọn ô có nguồn và chất lượng bảng

Ngày2026-10-31. Người dùng cho triển khai hướng RAG tổng quát sau nghiên cứu,
giữ yêu cầu không retry để làm xanh. Giữ toàn bộ diff chưa commit của các phiên
trước, không đổi source/OCR/compiler/publication/index/provider/quota/checkpoint.

## Thay đổi

- `knowledge/index/table_layout.py`: đặt ô trên lưới theo rowspan/colspan, phát hiện
  kích thước/span/lỗ/overlap sai, giới hạn bộ nhớ, chỉ nhận header tường minh.
- `table_dependencies.py`: chuyển thuật toán quan hệ native đã có sang knowledge;
  `rag/answer/table_context.py` giữ loader kiểm publication ghim. Không thêm suy
  năm hay từ điển ngành/câu hỏi. Nhánh native vẫn là heuristic giới hạn, không
  bảo đảm mọi bảng PDF/OCR đều nối được.
- Chunker v3 ghi quality và source dependencies dẫn xuất; IndexRun config có tổng
  fragment cần review theo input. Không thay source hoặc reindex đang phục vụ.
- `rag/answer/cells.py`: catalog từ evidence đã được cấp, header nhiều tầng,
  rowspan, quan hệ header/hàng nối cùng publication; chỉ cấp ô có citation đầy
  đủ. Model trả selector, backend copy chủ thể/header/giá trị. Giữ dấu gạch,0,
  dấu thập phân; không tính toán hoặc lấp ô trống. Bảnv2 sửa trùng ID khi ô
  rowspan và ô mới có cùng chỉ số trong danh sách, dùng cột vật lý; giữ đường dẫn
  nhóm/chủ thể để các hàng con không bị gộp thành một nhãn.
- Promptv8: JSON có lookups nội bộ; response statements/sources giữ tương thích.
  Chặn selector giả/trùng, numeric prose dẫn bảng, nguồn vi phạm text thuần.
  Trace có catalog hash/count và cell proofs. Việc chọn đúng hàng/cột với ý định
  vẫn cần kiểm chứng ngữ nghĩa, không được coi selector hợp lệ là câu đúng.
- Catalog prompt gom header và chủ thể hàng; raw structure nguyên vẹn. Chỉ bỏ
  duplicate body có exact JSON suffix. Guard cuối tính trọn evidence/catalog/
  quan hệ đọc trước reserve/chat; ModelOps tiếp tục kiểm framing/output.
- Thêm19 unit test trong `test_table_grounding_770.py`; nâng fixture API theo
  hợp đồng selector, thêm negative foreign_cell/numeric_prose, đổi assert version.
  Không sửa gold hay assertion nghĩa để lấy PASS model.

## Kiểm chứng thực chạy

CWD root, Python `backendV1/.venv/Scripts/python.exe -X utf8`; pytest từ backendV1.

- Ruff có phạm vi12file: PASS/exit0. Không sửa lint toàn repo.
- Nhóm trọng tâm (770,764,647,769,767): **55PASS**,2.42s,exit0.
- Full unit cuối `pytest tests/unit -q --tb=short --basetemp ../tmp/770-unit-v2`:
  **581PASS/1FAIL**,32.45s,exit1. Lỗi nền exact:
  `test_source_purge_716.py::test_accept_rechecks_publication_after_preview_before_preparing_purge`,
  `invalid_identity` tại `workspaces/access.py:39`. Full gate vẫn FAIL.
- Full unit trước lần sửa rowspan:577/1 rồi580/1; chạy lại sau thay đổi để kiểm
  batch cuối. Một test budget mới ban đầu truyền EvidenceSource thay SearchHit
  nên lỗi fixture; sửa fixture dùng SearchHit, giữ guard ứng dụng.
- Isolated API (scope672/answers648/hybrid655): **47PASS**,454.31s,exit0.
  Có faulthandler dump khi request scope chậm, không có testFAIL. DB riêng
  `qnu_v1_test_7b40bd64482e40ca` đã drop, legacy sentinel giữ nguyên. Không dùng
  DB đang phục vụ làm fixture. Đây là API/DB/Qdrant thật với model HTTP giả lập,
  không chứng minh semantic upstream.
- Sau sửa selector rowspanv2, nhóm API answers648 chạy kiểm lại riêng;
  kết quả cập nhật ở phần chốt bên dưới.
- Offline19 bộ primary/support đã lưu từ769: số envelope lớn nhất77042byte,
  không bộ nào vượt81920; cận input lớn nhất92501 theo thuật toán byte/framing,
  không phải tokenizer đo được. Không gọi model, không thay thứ hạng/nguồn.

## Model thật, một lượt mỗi câu

Cohort `rag-cells-once-770`, API ASGI/lifespan với auth thật, cùng assistantrev6,
Qwen đang được ModelOps chọn và index manifest cũ. Không chạy Playwright hoặc
restart serve. Ba caseF09/F12/F17 được chốt trước POST, idempotency riêng và ghi
dispatch trước gửi; policy mỗi capabilitymaxattempt1, không fallback.

- **2PASS/1FAIL**,49.141s. F12PASS bằng selector `E1:r0:k7`, đủ3evidence cho
  ô/header/chủ thể; F17PASS insufficient_evidence.
- F09FAIL `answer_cell_selection_required`: model tạo numeric statement dẫn
  bảng, bị guard chặn. Không có raw response để kết luận model định chọn số gì.
  Không gửi lại. Không đổi lỗi này thành no-data hoặc coi đây là F09PASS.
- Live dùng catalogv1, trước bản sửa ID/rowspanv2 cuối; không có lượt live mới
  trênv2. Hai case không chứa tình huống va chạm selector vẫn không được dùng để
  tuyên bố livev2/19câu đạt. Report giữ code hash và promptv8.
- Không đổi assistant/provider/capacity/quota/serving index. Dùng110460token,
  used9536641/reserved123455/còn339904 trên hạn10M; revisioncuối6.
- Audit đọc DB xác nhận3turn riêng/3hội thoại,3embedding/3rerank/3chat executions,
  toàn attempt1/codeok;2turncompleted/1failed. Index manifest/inference config giữ
  nguyên, quota không tăng và không có reservation unknown mới.
- Artifacts bỏ qua Git: `tmp/rag-cells-once-770/{admissions-answers,manifest,dispatches}.json`,
  `tmp/preflight770.json`, `tmp/context770-sizing-final.json`. Không đưa corpus/
  prompt/secret vào memory hoặc commit.

## Giới hạn và vận hành

Chưa hoàn tất nghiệm thu19câu; F09 vẫn lỗi tuân hợp đồng model. Không retry hoặc
gom PASS từ cohort cũ. Semantic review/gold độc lập đa định dạng vẫn NOT_RUN;
nhãn admissions còn draft. Verifier off/observe/enforce giữ policy hiện hữu,
không tự phát sinh lượt model kiểm chứng. Chưa có enumeration completeness hoặc
engine tính số chính thức. XLSX mới nhận upload, chưa extraction end-to-end;
không tuyên bố đã xử lý XLSX vì grid reader dùng được cho canonical cells.

Không cleanup/init/publish/reindex/restart. Người dùng cần nạp mã mới vào serve
bằng Ctrl+C rồi mở lại serve; index cũ vẫn đọc được. Quality reportv3 chỉ có ở
generation được tạo mới có chủ đích, không phải điều kiện để tiếp tục phiên cũ.

## Chốt kiểm chứng

API cuối trên catalogv2: `tmp/fix770_integration.py test_answers_api_648.py`,
**27PASS**,264.10s,exit0. DB `qnu_v1_test_0461a8e9c82c48b4` đã drop và legacy
sentinel giữ nguyên. Đây là lượt regression sau sửa rowspan, không phải model
thật hoặc retry cohort live. Nhóm3file trước đạt47PASS riêng, không cộng thành
74test độc lập. Cuối task Ruff12file, UTF-8/noBOM/LF19file và `git diff --check`
đạt. Không chạy frontend build vì batch này không sửa frontend.
