# Phiên581 — Nạp lại PDF, benchmark64 chưa chạy

Người dùng yêu cầu xóa dữ liệu DOCX, up PDF lại và chạy64 câu. Dùng qnu-knowledge-ingestion/qnu-rag-evaluation; kiểm context/diff/actor/DB-storage-model thật trước hành động, không sửa app.

DOCX Knowledge đã purge từ578: tombstone detached, 0revision/chunk/fact và không active index; không cần xóa lại. Giữ Repository/local DOCX và audit. Worker cũ chưa nạp sửa580; sau kiểm idle DB/Redis và process ownership, chỉ reload worker local bằng script repo. Giữ BE/FE/hạ tầng/config; worker startup không migration/seed.

IntakeHTTP202 dedup đúngrep_doc_acef7b5efd8b; importHTTP201 batchimp_batch_928bb61f08d3; worker job60f38f075fae completed. PDF revision2 ks_rev_d495e1fe0477 trên bnd_12190866d5ec, normalizerpdf-b62c983b8905d420caeed4c3be96. ActualMD/JSON/hash/projection/18manifestPASS; tải3formatHTTP200. Bảng1 16×12/header3/192ô khớp, Bảng3 mộtcột. Model giữ Luna chính/Qwen dự phòng.

Readiness NEEDS_ATTENTION70mục chặn,10limitations; vector-loadHTTP404SOURCE_NOT_FOUND do bindingpending, không tạoindexjob. 0vector/index mới, chưa publish. 64câu được giữ nguyên và kiểm IDs/hash, nhưng **NOT RUN/0modelcalls benchmark** vì chưa có PDF đang phục vụ. Không chạy nguồn rỗng rồi báo điểm. Không tự bỏ blocker hoặc áp semanticproposal.

[Báo cáo](../bao_cao/context581/PDF_REIMPORT_BENCHMARK_STATUS.md); evidence ignoredbackend/storage/context581 gồm preflight/worker-idle/intent/receipts,artifact thực, validation và benchmark-blocked. Preflight và validator/probeexit0; vectorBLOCKED; no appRuff/full rerun. Giữ mọi code/doc578–580; không commit/push/schema/modelchanges. Không tạo thread/gap test cần cleanup; import/revision mới giữ theo yêu cầu người dùng.
