# Phiên614 — Liên kết ngữ cảnh compiler và kiểm chứng ba DOCX

## Yêu cầu và phạm vi

Hoàn thiện mục → bảng → header → ô → chú thích, bổ sung regression và chạy lại compiler ba DOCX 2024–2026. Giữ nguyên nguồn/model/Quality Gate; không reindex, xuất bản, commit hoặc push. Bảo toàn toàn bộ thay đổi chưa commit từ các phiên trước.

## Thay đổi

Tạo navigation nguồn có proof, vị trí ô/header path, field notes và role candidate. Không nâng body thành header hoặc ghép note theo chữ trùng. Giữ source catalog/snapshot, tái kiểm structure/context khi đọc bundle. Truyền cùng evidence đến các bước compiler; gộp metadata lặp để không cắt raw context.

Planner đo đầy đủ source hashes/temporal navigation/prior selection và một phong bì correction tối thiểu. Actual budget giữ contract đo đúng request. Audit/repair tùy chọn quá budget ghi NOT_RUN, giữ missed/required và complete=false. Cap packet mặc định30 giữ, cho cấu hình server lớn hơn; fixture128packet/512call, model context24K/output8192 không đổi. Review explanation4096 là diagnostic, không nới verdict/proof/scope/year/condition.

11 file app thay đổi: runtime schemas; compilation catalog, coverage, engine, modelops hash, review, synthesis, cross_source, transport, validation; module structure mới. Test mới `test_compilation_structure_614.py`; test integration chỉ thêm prefix DB614. Không sửa parser/normalization/RAG serving/frontend.

## Kiểm chứng thực chạy

- Regression tái hiện thiếu context/cap/repair/explanation trước fix FAIL đúng nguyên nhân; những lệnh sai đường dẫn test exit4 giữ NOT RUN.
- Focused cuối88PASS/exit0;21test mớiPASS; Ruff13filePASS/exit0.
- Full cuối3622PASS/18FAILnền/17SKIP,+23subtestsPASS,741,75s/exit1. Exact so613:0failuremới/0causeđổi/0IDthiếu; full vẫnFAIL. Full trước bước cuối3618/18/17 giữ lịch sử; run bị dừng làINCOMPLETE.
- Real compiler:102entities/116assertions/36sections/36groups/18relations candidate;381proof giữ,129selected/42packets,116/116assertion cósection; exactserviceStorage readback. `needs_attention`, chưaAPPROVED/chưa xuất bản.
-54unknown đều null;37unresolved/1contradicted;15literal scope issues;9missedproof;1repairNOTRUN. Các count có thể trùng, không tính thành quality score.
- Manual review:1.070 gắn đúng thạc sĩ, chưa verified header;3.362 không còn affirmative quota giáo viên;**5.081 vẫn bị model gán quota mặc dù nguồn là số trúng tuyển đã nhập học**, item/section reviewer false supported. Đây là finding chặn duyệt.
- Lượt cuối261call thật; tái dùng72call topic có immutable receipt/request khớp. Toàn phiên442call thật, tất cảstop/0fallback/max4157output; không giấu các lượt lỗi. Medium/8192 được ghi trên wire; không kết luận provider thiếu context.

Lệnh/cwd/exit/JUnit trong [Validation](../bao_cao/context614/VALIDATION_REPORT.md), [exact IDs](../bao_cao/context614/TEST_ID_COMPARISON.md), [báo cáo thật](../bao_cao/context614/LIVE_COMPILER_REPORT.md). Runner dùng Python3.12 venv, subprocess `-m pytest -v` từbackend; khôngCLI/modelAPIfallback.

## Cô lập và bảo toàn

Xác minh DB/MinIO/Qdrant loopback trước chạy. Dùng5DBtest có nonce và LocalStorage riêng; khôngmigration/schema write nguồn. Copy typed defaults vào test khôngcredential. Đã dọn cả5DB và xác nhận tên không còn; giữStorage bằng chứng theo chính sách bảo vệ, không bypassdelete.

Seals nguồn/shared rows/provider/defaults giữ; default gh/gpt-6-luna không đổi, compiler dùng GPT-OSS medium như trước trong process riêng.2943Qdrantpoints/fullpayload hash giữ/0retrievable, không đọc float vector. Nguồn raw/canonical/snapshot giữ. Khôngindex/publish/restart/deploy/stage/commit/push; branchv1.0.1/HEAD09d254da giữ.

## Giới hạn và bàn giao

Đây là fixture compiler thật dùng canonical ghim, không fresh parser/QG ingestion/browser/publishedE2E hoặc benchmark64. Bộ ba nguồn không có explicit field-note; regression độc lập kiểm đường này. Không tự duyệt hoặc sửa candidate5081 để làmPASS. Đề xuất kế tiếp: hợp đồng metric role/nhãn nguyên văn và kiểm chứng vai trò trước chuẩn hóa nhãn; cần tránh từ điển vá theo ca.
