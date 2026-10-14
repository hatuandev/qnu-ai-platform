# Phiên 435 Kiểm thử chatbot sau khi thêm văn bản thuyết minh

Ngày 2026-10-14. Người dùng đã duyệt, nạp vector, xuất bản nguồn mới và yêu cầu test. Phạm vi: 20 câu đại diện từ bộ 82 trên cả RAG/DAG, đối soát và đề xuất; không sửa runtime.

## Thực hiện

Dùng skill qnu-rag-pipeline và qnu-chatbot-builder để kiểm chứng retrieval/claim/citation theo nguồn đã xuất bản và quan sát pipeline, không lấy HTTP200 làm accuracy. Đọc canonical nguồn mới, xác nhận binding/index/hash trên snapshot epoch4/20 nguồn. Tái dùng `scripts/evaluate_evidence_417.py`, câu hỏi gốc/expected cục bộ, hội thoại riêng mỗi lượt; không ghép các batch cũ.

Artifact tạo: `backend/storage/admissions_eval435_smoke20.json`, `backend/storage/admissions_eval435_audit.json`. Tệp báo cáo: `docs/kiem_thu/2026-10-14_20_cau_rag_dag_sau_them_van_ban_thuyet_minh.md`. Đồng bộ journal index, PROJECT_CONTEXT, snapshot435 và WORK_LOG. Không sửa mã BE/FE hay harness.

## Kết quả

40/40 HTTP200; DAG16answered/4insufficient, RAG16answered/4insufficient, không quota. Median15,23/11,37 giây, max34,42/34,17. 125 successful usage logs (123 GPT-OSS,2Gemma fallback),939393tokens. 34/34 decision integrity,57/57 canonical span/hash; không phải entailment/accuracy/Ragas. 20 lượt trích nguồn mới. Config/publication/tập runtime fingerprint theo dõi không đổi.

Cải thiện quan sát: DQN/hotline/chỉ tiêu5173, đủPT1–5+tuyểnthẳng, khôngnhânTiếngAnh, crossyear điểmchuẩn chỉthamkhảo, họcbổng2025khôngcamkết2026. Lỗi quan trọng: câu16 RAG gánPT3 phùhợpTHPT, verifier vẫnsupported; câu13targetinstitution=ĐHSPHàNội thayQNU; câu11DAG chọn2025 rồinoanswer;38cảhai/48RAG/62RAG khôngtrảdùcóchỉdẫn. Missingqualifiers số53/56,15/30loạiđiểm,22,5ngưỡng,17giờ,10tháng/năm vàeligibility. DAG16/75 partial vìclaimthừa.

Không full suite/Ruff/Vite vì không đổi runtime hoặc mã nguồn. Hai bước chuẩn bị bị lỗi cú pháp one-liner và stdout cp1252, đã sửa câu lệnh/chạy UTF8 trước batch; batch chốt hoàn tất bình thường. Sandbox chặn socket ban đầu, live checks chạy được qua quyền phù hợp. Không reset/reindex/publish/config/restart/can thiệp backup.

## Bài học và tiếp quản

Exact citation không bảo đảm suy luận đúng; phải kiểm từng quan hệ và điều kiện. FAQ tổng hợp trùng nội dung benchmark nên không phải eval độc lập. Không ép tất cả câu trả lời được, nhưng no-answer dù có nguồn cần phân tích. Đề xuất atomic semantic claims, target/organizer roles, year/context/qualifier coverage và partial recompute trước full82. Chưa được yêu cầu sửa lỗi ở lượt này; giữ kho và cấu hình hiện tại, backup paused.

[Báo cáo đối soát](../kiem_thu/2026-10-14_20_cau_rag_dag_sau_them_van_ban_thuyet_minh.md).
