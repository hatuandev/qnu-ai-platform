# Phiên613 — Compiler theo nhóm và ngân sách theo model

## Yêu cầu và phạm vi

Người dùng duyệt triển khai các đề xuất sau điều tra612: ngân sách theo model, chia nhóm giữ context, manifest tổng, tổng hợp nhiều tầng, đối chiếu nguồn có bằng chứng, checkpoint và lỗi rõ ràng; regression và thử ba DOCX. Giữ source/Quality Gate/model mặc định, không reindex/publish/commit/push/restart/deploy. Dùng skill mã sạch, backend và ModelOps; không tạo subagent.

## Thay đổi

- Bổ sung profile context/output gắn alias/endpoint vào ModelOps, kiểm output trước key lease cho generate/stream. Capability cập nhật từng phần không xóa profile chưa hiển thị trên form cũ. Không sửa cấu hình provider thật; profile thiếu vẫn công bố fallback server chưa xác minh.
- Giữ Draftv1 và thêm Manifestv2/danh mục nhóm. Tổng92entities/145assertions không còn bị ép vừa64/128của một request. Giữ source/hash/ID/unknown/provenance/condition/exception và coverage toàn cục khi đọc lại.
- Tính tổng hợp/review riêng, bỏ reserve5.000 của synthesis planner; review quá lớn chia nhóm vẫn giữ raw context. Quan hệ giữa nguồn là candidate từ nhãn tổng quát, cần raw proof, review độc lập và blind direction. Ngân sách CPU tìm cặp tách khỏi inference; phần chưa kiểm giữ incomplete/pending, không giả negative fact.
- Lỗi capacity422 có stage và status riêng, không tự retry hoặc dùng làm lineage. Checkpoint source/config/actor/version vẫn giữ, không chuyển dữ liệu cũ khác protocol thành đã kiểm mới.
- Phạm vi17appfiles và2testfiles so với đầu613. Không sửa parser/FE/index/publication/migration. [Triển khai chi tiết](../bao_cao/context613/IMPLEMENTATION_REPORT.md).

## Kiểm chứng thực chạy

Môi trường dev/local xác minh DB/MinIO/Qdrant loopback; DB thử prefix613+nonce, LocalStorage riêng. Baseline3test mới FAIL/exit1 trước sửa; negative review/direction2FAIL trước fix tương ứng. Chốt focused70PASS/84,61s/exit0 gồm15regression mới. Ruff19file PASS/exit0.

Full cuối từ root qua helper `context613_acceptance_checks.py run --label full-final`, thực chạy `backend/.venv/Scripts/python.exe -m pytest -q` ở backend, DB riêng: **3601PASS /18FAIL nền /17SKIP,+23subtestPASS**,708,05s,exit1. Đối chiếu exact IDs/cause với611full3586/18/17:15mớiPASS,0newfail/changedcause/missing. Tổngsuite vẫnFAIL. Các full bị dừng để sửa và lần bị ngắt86% giữINCOMPLETE; không cộng dồn thànhPASS.

Thử ModelOps thật GPT-OSSmedium/output8192, context24K fallback chưa xác minh, không đổi primarygh/gpt-6-luna. Hash raw3DOCX/canonical381proof khớp. Đọc-only288object thử611,91completed+5knownrejects đủ96identity replay; không gửi lại96calls. Candidate fixture import có provenance, không phải migration production hoặc parser mới.

Compiler hoàn tất92entities/145assertions/25sections/16groups/9relations ứng viên, bundle lưu/đọc qua service khớp. Toàn145giá trị/state/source/scope/condition/exception giữ nguyên.36calls tổng hợp+1probeđầu+17cross=**54calls mới**;allstop/0fallback,max2475output,263475input/45158output. Chỉ chứng minh medium sent, upstream không echoeffort. ChưaAPPROVED:10/21packet chưa complete,5scopeissues,17missedproof refs;13assertion unresolved/1contradicted;2section chưa supported,1relation unresolved và2directionissues; số đếm có thể chồng lấp. Cross xét12/31cặp,19chưa xét.

Đối soát sơ bộ145ứng viên còn thấy sai mức đào tạo, nhầm cột khảo sát thành chỉ tiêu giáo viên và absence claim cục bộ bị rộng phạm vi. Không sửa source hoặc xóa/gộp ứng viên để xanh. [Đối soát](../bao_cao/context613/RECONCILIATION_REPORT.md), [chạy thật](../bao_cao/context613/LIVE_COMPILER_REPORT.md).

## Dữ liệu, dọn dẹp và giới hạn

Shared rows/seals sau cùng khớp collection5/binding24/source12/index37/assistant5/provider13. Raw3DOCX và2.943Qdrantfullpayload/0retrievable giữ. App/testhash khớp mã đã chạyfull; ngoài17appfiles giữ nguyên. Khôngstage/commit/push.

Năm DBtest613 đã drop đúng tên+nonce và xác nhận không còn. Storagetạm/bằng chứng giữ policy bảo vệ, không bypass xóa đệ quy. Không gọi LLM sau crossvalidationcuối. API/model tests không được gọi là browser/servingE2E; FE/build/benchmark64/parser mới/vector/publication **NOT RUN**.

Một lệnh nhầm testfilename exit4/no tests; fixture ID dài sai VARCHAR36 được sửa riêng; preflight storage eager export và idempotency trùng bị chặn trước inference. Mọi receipt giữ để truy vết. Full cuối không chạy trên DB hoặc kết quả dở của các lần đó.

## Bàn giao

[Kiểm chứng](../bao_cao/context613/VALIDATION_REPORT.md), [test IDs](../bao_cao/context613/TEST_ID_COMPARISON.md), [thiết kế](../bao_cao/context613/DESIGN.md), [cấu hình profile](../bao_cao/context613/MODEL_LIMITS_GUIDE.md). BảnMarkdown/JSON thử có thông báo chưa duyệt ở backend/storage/context613/exports. Chỉ hoàn thành phần compiler có thể tổng hợp; nội dung cần review và19cặp chưa kiểm, chưa đủ xuất bản. Chưa bật profile context thật hoặc restartdịchvụ.
