# Phiên772 — Sửa phản hồi chọn ô kèm văn bản F09

Ngày2026-10-31, user cho sửa lỗi F09 sau chẩn đoán771. Phạm vi: hợp đồng trả lời
và projection trong RAG v1; không thay nguồn/corpus/gold/index/ModelOps/quota.
Đã đọc context, Git/diff, clean code/backend/RAG/evaluation và gate chung.

## Nguyên nhân và phương pháp

771 xác nhận model đã chọn đúng ô nhưng viết numeric statements cùng lookups,
khiến guard từ770 từ chối toàn lượt. Chỉ nới guard nhận mọi số trong prose sẽ
cho model thêm số/điều kiện không được kiểm chứng, nên không dùng cách đó.

Khi có selector hợp lệ, backend lấy đáp án hoàn toàn từ catalog ô nguồn, bỏ toàn
bộ model statements. Trace ghi `grounding.projection` version/mode/số ý bị loại.
Không phân loại bằng từ khóa test, không tính toán hoặc chép số từ model vào ô.
Không có lookup mà prose dẫn số từ bảng vẫn chặn; lookup ngoài catalog/trùng,
schema/citation/text sai vẫn bị từ chối. Narrative thuần vẫn giữ luồng cũ.

Sửa `cells.py`, `drafting.py`, `service.py`; promptv8→v9,
`qnu.answer-projection/v1`. Thêm6unit regression trong772, API case mixed_lookup,
cập nhật assert promptversion. Không có migration/dependency/frontend mới.

Đã thông báo user trước khi áp dụng rằng phần prose không xuất ra và có trace.
Đây là đáp án trích ô; chưa bảo đảm đủ mọi điều kiện nằm ngoài ô. Không coi
selector hợp lệ là tự động đúng ý định hoặc verifier ngữ nghĩa.

## Kiểm chứng

Python backendV1 venv, từ root hoặc cwdbackendV1 theo lệnh.

- RED: `pytest tests/unit/test_lookup_projection_772.py -q --tb=short`:
  3FAIL/3PASS,exit1; mixednumeric bị guard chặn, mixedtext không số bị xuất thừa.
- Sau sửa: nhóm772/770/764/769 **40PASS**,3.23s,exit0.
- Ruff6file sửa PASS/exit0, `git diff --check` PASS. Khôngauto-fixngoàiphạmvi.
- Fullunit `pytest tests/unit -q --tb=short --basetemp ../tmp/772-unit`:
  **587PASS/1FAIL**,46.74s,exit1. Lỗi nền exact716:
  `test_accept_rechecks_publication_after_preview_before_preparing_purge`,
  `invalid_identity` tại `workspaces/access.py:39`. FullgatevẫnFAIL.
- API cô lập: `tmp/fix772_integration.py test_answers_api_648.py`, **28PASS**,
  295.45s,exit0. Bao gồm numeric prose không lookup/foreignID/mixedlookup/
  withdrawal/scope/provider/reasoning, không chỉ helper. Có faulthandler dump
  lúc test đầu chờ source bundle, nhưng không có testFAIL. DBriêng
  `qnu_v1_test_6b6b0f8b66b94bf3` đãdrop,legacy sentinel giữ nguyên.

## F09 model thật, một lần sau sửa

`tmp/live_f09_fixed772.py`: cohort mới `f09-fixed-once-772`, ASGI/auth thật, không
restart serve hay đổi config. Snapshot cũ/assistantrevision6 giữ, candidate50/
top20/budget81920, Qwen ModelOps hiện có, promptv9/catalogv2/projectionv1.

**1PASS/0FAIL**,20.672s,exit0. Model trả statements rỗng và selector đúng ô;
backend trả giá trị22 cùng citation ô/header, không có prose model bổ sung.
Projectiontrace selected_cells/omitted0. Chat28280prompt/23completion/28303total.
Audit `tmp/audit772.py` exit0:1turncompleted/1hội thoại, mỗi capability
embedding/rerank/chat1execution,toànattempt1/codeok. Không fallback/retry hoặc
gộp PASS với770/771. Total3capability36632token, maxevidence68699byte.

Quota10Mgiữ,used9610050/reserved123455/còn266495,khôngunknownreservationmới;
indexmanifest/inferenceconfig giữ nguyên. Không upload/compile/publication/reindex/
cleanup/init hoặc sửa checkpoint. Raw response chỉ trong ignoredtmp, không đưa
inputprompt/secret/corpus vào Git. Đây chưa là đủ19câu/semanticreviewđộc lập.

## Chốt

API hoàn tất28PASS,không chạy lại model. Ruff6file/diff/UTF8noBOM/LF13file và
localdoclinksPASS. User mở lại serve để nạp code mới, không cần dọn hoặc tạo lại
phiên có publication/index hợp lệ. FrontendbuildNOT_RUN vì khôngsửaFE.
