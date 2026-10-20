# Phiên563 — Điều tra EVIDENCE_CONTEXT_MISSING

Người dùng hỏi lỗi có do Qwen context 32K không. Đọc mã/config/usage hiện tại, giữ toàn bộ sửa chưa commit. Skill RAG pipeline và clean code; không sửa app.

Đọc local trong transaction READ ONLY, không gọi LLM mới. Usage đúng hội thoại562: Qwen success 543+133 và 4786+52 token, không fallback; lỗi 409 được backend sinh, model overflow có mã riêng.

Probe nguồn published272canonical/6fact: full closure PASS. `_fact_groups` kiểm source row nhưng không giữ trong group; pack một fact thành4block/8057chars, thiếu row,0group bịdrop. Claim projection → dependency_intros → dependency_groups → _fact_groups/exact tái hiện409 không model. K5/36000 và K100/10000000 đều lỗi; mô phỏng thêm đúng1canonicalrow đạt closure/projection. Không áp bản sửa, không coi probe là E2E PASS.

Mã lỗi không do context32K của hai request đã chạy. Chưa có fullstack/plan của lượt live cũ, không kết luận đây là nguyên nhân duy nhất mọi409. Hướng sửa: giữ source row/dependency atomic và regression pack→projection, không nới guard hoặc nâng model window để che lỗi.

Probe Python exit0; không fulltest vì không đổi app. Không app/config/DB/source/index/publish/restart/deploy/Git writes. Evidence private context563/diagnosis.json giữ; không testDB/runtime mới cần cleanup.

[Báo cáo](../bao_cao/context563/DIAGNOSIS.md).
