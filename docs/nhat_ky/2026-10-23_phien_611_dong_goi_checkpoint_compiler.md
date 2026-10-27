# Phiên611 — Đóng gói và checkpoint compiler

Người dùng yêu cầu sửa packing/checkpoint rồi chạy lại ba DOCX2024–2026 bằng GPT-OSS medium/output8192, giữ nguồn/Quality Gate và không reindex/publish/commit/push. Thực hiện qua ModelOps trong DB/Storage thử cô lập; giữ primary gh/gpt-6-luna và các thay đổi608 có sẵn.

Policy thống nhất packing/request/config hash; explicit reasoning_effort qua adapter; tách ngân sách extraction/review, giữ raw context khi chia item review; lossless existing-assertion contexts. Checkpoint từng logical call có ordinal/hash/source/config/actor, durable started/completed/rejected, không resend stage không xác định. Auth/OCC/idempotent resume với tổng counter kế thừa, ghim cache và audit riêng. Không migration DB; không hạ validation.

Repro4FAIL/1SKIP trước sửa. Các focused trung gian có failures được lưu riêng; chốt59PASS, concurrency2PASS, Ruff14PASS. Full chốt3586PASS/18FAILnền/17SKIP,+23subtestPASS,exit1/769,57s; exact608IDs/cause giữ,22test mớiPASS,0newfailure/missing/causechange. Hai lượt bị dừng được ghi INCOMPLETE, không ghép thành PASS. [Kiểm chứng](../bao_cao/context611/VALIDATION_REPORT.md) và [test IDs](../bao_cao/context611/TEST_ID_COMPARISON.md).

Compiler thật96calls GPT-OSS/0fallback, wire medium/8192, tất cảstop/max5295output, usage482090input/151499output.54calls đầu dừng tại coverage request25459>24K trước inference; sửa lossless packing còn23076. Resume dùng nguyên54stages cũ,42calls mới;91completed/5contractrejected/96ordinalunique, Storage/audit/readbackPASS. Không có stage started/uncertain bị gọi lại. Upstream khôngechoeffort, không khẳng định độc lập mức reasoning đã thực thi.

Toàn compiler chưa đạt:92entities/145assertions vượt hợp đồng64/128 khi ghép, không phải context/output exhaustion. Exactdedup vẫn92/145; không tự gộp ngữ nghĩa/nângcap/cắt nguồn đểPASS. Chưa synthesis/bundle/Markdowncuối/approval. Job cuối kc_182025997c28481f83f32890cc2ce77f; read-only replay xác minh đúngjob thay cho receipt helper chọn nhầm parent. [Live report](../bao_cao/context611/LIVE_COMPILER_REPORT.md), [thiết kế](../bao_cao/context611/DESIGN.md).

Postcheck nguồn/sharedrows/modeldefaults/vector2943/0retrievable giữexact;11appfiles sửa đúngscope, cácfilekhác giữ. Bốn DB611sởhữu đãdọn, Storagegiữpolicy. Full/realcompiler dùng cácDBkhácnhau; khôngproductionwrites/reindex/publish/restart/Gitwrites. FE/64/browserE2ENOTRUN. Bước còn lại là review relevance/scope và thiết kế nhóm bản biên soạn lớn có provenance, không tăngtoken mù.
