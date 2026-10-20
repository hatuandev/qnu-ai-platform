# Phiên572 — Benchmark RAG và DOCX staging

Người dùng cho triển khai đề xuất: benchmark64 cùng nguồn trước; tạo revision DOCX mới, đối chiếu MD/JSON rồi staging vector, chưa publish; giữ nguồn cũ, model và Git. Không dọn toàn kho.

Benchmark52/60=86,67%,positive43/50,negative9/10,social4/4;8FAIL gồm X07provider ReadTimeout503. 6gains/5losses so568; cùng frozen query/gold/source/index, không judge call. Nguồn cũ262points giữ,58threads/13gapsdọn.

Live parser phát hiện trạng thái cờ literal_only không hợp lệ, rồi nhánh projection vẫn coi native unknown header là blocker. Sửa tối thiểu trạng thái diagnostic confirmed chỉ sau exact native grid proof; unknown/ambiguous/literal-only restrictions còn, không semantic approval hoặc đổi gate policy. Hai revision bị chặn được giữ; revision5 ks_rev_d5135c27d130 READY_WITH_LIMITATIONS/0blocker. 233blocks/10tables/53items/3notes/517fields giữ; facts415 so368 (60added/13notmaterialized, raw còn); gold numeric/year giữ. Index idx_rev_91267ceb54ff ready262chunks/415facts/262stagingpoints; chưa publish. Preview4/6, P06/P08FAIL; D01rangePASS; không phải full new64 benchmark.

Focused109+23subtests/RuffPASS; full2838PASS/18FAIL/17SKIP, exact571IDs/causes/0newFAIL/1newPASS; full vẫnFAIL. Một full-run đang giữa batch bị ngắt, chỉ nghiệm thu full-complete cuối. DBtestdọn; Storage runtime572 xóa bịautomatic-reviewblocked, giữ/no bypass. Không FE change/commit/push/restart/deploy/modelchange/pub. Chỉ native fidelity parser và test sửa ở task này.

Chi tiết và commands/exit/IDs: [benchmark](../bao_cao/context572/BENCHMARK_REPORT.md), [đối chiếu64](../bao_cao/context572/CASE_COMPARISON.md), [DOCX staging](../bao_cao/context572/INGESTION_REPORT.md), [kiểm chứng](../bao_cao/context572/VALIDATION_REPORT.md). Bằng chứng riêng ignored trong backend/storage/context572.

Giới hạn: gold là devset chưa human signoff; preview khác assistant API; còn RAG lỗi và 18 full failures. Cần xử lý những câu còn lỗi, đo tiếp staging có kiểm soát trước khi quyết định xuất bản; không tự publish revision này.
