# Phiên 544 — Đề xuất ngữ nghĩa có duyệt, mapping và tìm kiếm DOCX

Bắt đầu ngày 18 và kết thúc ngày 19/10/2026 (Asia/Bangkok); giữ số phiên và đường dẫn theo ngày bắt đầu.

## Phạm vi được giao

Xử lý khoảng hở của thử nghiệm offline phiên 543. Người dùng chọn **ModelOps tạo đề xuất, duyệt trước khi áp dụng**. Giữ nguồn, không dùng từ điển viết tay phân loại chú thích/ý nghĩa ô. Sửa theo batch trước kiểm thử theo yêu cầu người dùng. Không commit/push, nạp lại nguồn, thay cấu hình model, duyệt nguồn thật hoặc xuất bản.

## Thay đổi

- Thêm `semantic_annotations.py`: schema đề xuất scope table/row/group/column và cell state; exact quote, exact coordinates, hash nguồn/đề xuất và actor/lý do. Staging kiểm trên bản sao, không thay trường, facts hoặc graph. Ô trống, số và mã số không được model đổi nghĩa; căn cứ trong cùng dòng phải thuộc chính ô, không mượn ô bên cạnh.
- Endpoint tạo đề xuất gọi ModelOps theo cấu hình DB; endpoint đối chiếu chỉ sửa metadata dẫn xuất của bản nháp `review_required`. Cùng lock nguồn/kiểm tra idle, collection/revision binding và pair/hash. Session inference riêng để commit accounting không giải phóng lock nguồn. Pending/stale/unavailable không được duyệt toàn nguồn bằng đường tắt.
- Luồng ingestion opt-in hiện có chạy đề xuất trên projection chuẩn cuối cùng, tránh gọi trên projection legacy rồi mất đề xuất. Không bật hoặc sửa policy đang chạy. Có thao tác tạo đề xuất thủ công trong hộp thoại kiểm duyệt.
- Lưu dependency riêng theo cột. Toàn dòng có thể đóng gói đầy đủ context, nhưng fact chỉ nhận shared refs và refs đúng cột. Header GFM cũng là dependency độc lập. Giữ tương thích hash manifest cũ khi trường mới rỗng.
- Giao diện hiển thị bảng/dòng/cột, trích đoạn và trạng thái được đề xuất. Cần xác nhận đã đối chiếu, ghi chú và hash hiện hành; có áp dụng vào nháp hoặc bỏ đề xuất. Áp dụng không chuyển active revision, không xuất bản. Giữ auth header khi gọi API review.
- DOCX mapping dùng trọn unit trên native preview khi chỉ có một trang khớp; hỗ trợ marker danh sách chữ cái, không bỏ chữ số. Dòng ngắn chỉ suy trang khi hai hàng bao quanh đã ở cùng trang. Ảnh chỉ định vị khi khớp pixel và một occurrence duy nhất. Locator/bytes/quality flags được giữ nếu chưa chắc.
- BM25 tách từ trong identifier có underscore, dùng header context nhẹ cho dòng ngắn, không trả structural header như dữ liệu. Tăng trọng số mã có số 0 đầu xuất hiện nguyên văn trong câu hỏi gốc; không lấy mã từ query expansion của model.

## Kiểm chứng thực chạy

Cwd root `D:/DuAnPhanMem/qnu-ai-platform`, trừ full suite chạy trong `backend` và frontend chạy trong `frontend`. Dùng Python/Ruff của `backend/.venv`, không cài dependency.

- Focused: `python -m pytest -q` với `test_semantic_proposals.py`, `test_knowledge_units.py`, `test_docx_source_evidence.py`, `test_qnu_header_and_cell_states.py`, `test_review541_fixes.py`, `test_review536_findings.py`, `test_qnu_serving.py`, `test_evidence_retrieval_regressions.py`, `test_prose_selection_502.py`: **175 PASS**, exit 0, 8.37s; 31 ca mới. Lượt 139 PASS trước đó chưa bao gồm hai file regression retrieval/prose. Lượt đầu 3 FAIL do hai fixture pointer chưa phù hợp và assertion hash lịch sử chưa loại trường mới; đã sửa fixture/assertion, không làm yếu guard ứng dụng.
- Ruff scoped trên 19 file Python: **PASS**, exit 0. Lượt đầu phát hiện import format và nested-with trong code mới; đã sửa. Một lệnh Ruff lúc bắt đầu full dùng sai đường dẫn từ cwd backend, **NOT RUN** ở lệnh đó; chạy lại đúng root đã PASS.
- Frontend: `node --test src/features/knowledge/components/semantic-review-preview.test.mjs`: **4 PASS**, exit 0. Chạy component thật qua React SSR và API thật với HTTP mock: escaped quote/coordinate, trạng thái pending, Authorization/hash/revision, lỗi stale không thành success.
- Biome trên 5 file frontend sửa, `--line-ending=lf`: **PASS**, exit 0. Cấu hình formatter mặc định CRLF xung đột yêu cầu LF của AGENTS; dùng override lệnh, không sửa config. `npm run build` gồm TypeScript: **PASS**, exit 0. Chưa kiểm giao diện tương tác trong browser; SSR/build không chứng minh layout thực tế.
- Runner offline mới `.antigravity-bridge/validation/check_rag544_offline.py`: **PASS**, exit 0. Cùng DOCX/preview checksum phiên 543, pair valid; đủ 183 đoạn, 10 bảng/103 dòng/645 ô không rỗng, 3 footnote/anchor, ảnh bytes và 261 citation exact span. `page_unresolved` 9 → 1; giữ cảnh báo header chưa có vai trò xác minh và ảnh chưa phiên âm.
- Đối chứng cùng corpus canonical hiện hành và cùng 20 gold-coordinate nháp: BM25 baseline **Hit@5 .85 / MRR .825**, hiện tại **Hit@5 1 / MRR .891667**. Cải thiện trên một nguồn; không phải benchmark production hoặc chứng minh dense/hybrid/rerank/generation.
- `evaluate_rag544_offline.py`: **NOT_READY**, exit 1. Các note scope và hai cell state của nguồn thật vẫn chưa đổi vì chưa có đề xuất đã được người dùng duyệt. Ba ô ambiguous tiếp tục bị gate chặn; không coi ranking đạt là toàn pipeline đạt.
- Gọi thật `propose_rag544.py` qua ModelOps đã cấu hình: **FAIL — ALL_PROVIDERS_UNAVAILABLE**. Không có đề xuất thật, không tự điền bằng gold labels, không đổi provider/model/config hoặc dùng model API fallback. Script lưu report lỗi rồi exit 0; exit này không phải inference PASS. Token/cost upstream chưa có kết quả xác nhận. Chỉ hành vi accounting/health thông thường của ModelOps có thể phát sinh; không ghi source/revision thật.
- Full đầu **FAIL 16 / 2191 PASS / 17 SKIP / 23 subtests**, exit 1, 212.86s: ngoài 13 lỗi nền có 3 regression mới ở cache/section/prose selection. Nguyên nhân header_context legacy chứa toàn nguồn; đã giới hạn chấm điểm header cho typed table units, không đổi assertion để che lỗi. Focused 175 PASS gồm cả 3 ca, BM25 MRR cuối .891667. Full cuối **FAIL 13 / 2194 PASS / 17 SKIP / 23 subtests**, exit 1, 209.84s: exact 13 IDs khớp baseline 542, không ID lỗi mới. Tổng suite vẫn FAIL. Bằng chứng `fix544-full-final.xml` và `fix544-baseline-compare.json`.

Bằng chứng local trong `backend/storage/fix544-*.log`, XML và `backend/storage/rag544-offline/`; không đưa corpus/proposal vào Git. Giữ nguyên artifact/reports phiên 543.

## Giới hạn và bước tiếp theo

Tài liệu thử là dữ liệu giả lập, không phải dữ liệu tuyển sinh QNU chính thức. Cần xử lý tình trạng provider trong ModelOps rồi tạo đề xuất, đối chiếu đúng trích đoạn/phạm vi và duyệt riêng metadata nháp. Sau đó mới chạy lại evaluation và xử lý các unknown còn thực sự thiếu căn cứ. Mã chưa tự cập nhật các nguồn đã lưu; không nạp lại, reparse, index, approve, publish hoặc restart trong phiên này.
