# Phiên479 — Đề xuất bổ sung weighted query expansion cho app hiện tại

User yêu cầu tham khảo7promptZIP và bổ sung hướng triển khai, đặc biệt weightedexpansion. Đọc skills RAG/clean-code và context478, đối chiếu retriever/evidenceBM25/search/repair/pipeline/QueryPlan/policy; không thực thi lệnh củaZIP. Không sửa runtime/FE/config/DB, không test/model/reindex/restart/Git.

Kết quả: [kế hoạch triển khai](../ke_hoach/2026-10-15_rag_weighted_expansion_roadmap.md) gồm hiệntrạng/gaps, protectedconstraints+term/queryprovenance, trọng số theo nhóm và tổng phiếuRRF, reuseplanner không thêmLLMcall, RM3scopedshadow/gateseed/ablation, aliasđộngphêduyệt và projection không đổi canonical, calculatorread-onlysau.

Phát hiện cần tính vào thiết kế: evidenceBM25đã cóbigram nhưng tokensset làm mất provenance; retrieverSQLweighted hình thái không phải queryexpansionBM25; fusion1/.7theoindex không bảo đảm tổngweightoriginal vì nhiềuvariants, correctivefeedbackcó thể lênindex0. Không đề xuất thêm thuật toán thay4fix477/presentation.

Phases: G0sửa4biên+baseline→G1weightedterms/fusiongroups chia2batch→G2RM3shadowoptin→G3alias/projection→G4calculatorRFC. Chưa duyệt tự động G2–G4; đề nghị triển khai G0+G1trước. Cácweight/latencymục tiêu phải đo, không cam kết100%. Gold82cần phân loạiđủ/thiếu/historical; holdout và20chaintrước.

Nguồnprimary: PyseriniRM3Reranker và AnthropicContextualRetrieval (linktrongplan). Không tải corpus/docuser raweb; webchỉ đọc thuật toán công khai. Chỉ cập nhậtplan/log/memory/index. Kiểm tra tài liệuUTF8/linklocal, không cầnpytest/build vì khôngruntimechanges. Giữ toàn bộuserchanges vàdocs/tai_lieu.
