# Phiên 444 — Sửa lỗi đủ ý, phạm vi nhóm và tính dùng được của chat RAG

Ngày: 14/10/2026, Asia/Bangkok. Tiếp nối phiên 443 theo đúng thứ tự người dùng giao (6/9, 13, 25, 62/75).

## Mục tiêu và giới hạn

Sửa các lỗi chất lượng trả lời còn lại của chatbot tuyển sinh bằng thay đổi nhỏ, có kiểm chứng; không xây lại RAG. Đọc `AGENTS.md`, `PROJECT_CONTEXT.md`, nhật ký 443 và 4 skill (`qnu-clean-code-architect`, `qnu-backend-architect`, `qnu-rag-pipeline`, `qnu-chatbot-builder`). Git sạch lúc đầu phiên (không thay đổi đang có). Không đổi model/provider/reranker/token/quota, không reset DB, không nạp lại vector, không xuất bản lại kho, không khôi phục DAG, không backup, không sửa frontend. Không commit/push.

Phương pháp tổng quát đã trình và được người dùng duyệt kèm 5 điều kiện (không lọc yêu cầu có số trong câu hỏi; giữ "một số ngành phù hợp"; nối đoạn cùng tài liệu/phiên bản/mục/kề thứ tự; công thức kèm biến + điều kiện + nguồn; thiếu URL thì nói rõ, không thay cổng chung). Mọi thay đổi dùng bất biến cấu trúc (dấu câu, hoa/thường, marker danh sách, hình dạng số/URL/alias), không hardcode đáp án, ID câu, tên ngành, từ vựng hay tên model vào runtime (ID câu chỉ trong test).

## Đối chiếu mã và nguồn thực tế (không dựa vào báo cáo)

- Câu 6/9 false-partial: verifier `complete=true` nhưng indexed audit tự thêm yêu cầu (6 đòi cộng 28 bổ sung vào tổng dù câu hỏi không hỏi; 9 để `retained_by=[]` dù 5 claims phủ đủ PT1–PT5). Trạng thái partial đến từ audit, không phải thiếu nguồn.
- Câu 13: đáp án supported chỉ là 1 hàng fact Sư phạm Tiếng Anh; đoạn chính sách nhóm ("Một số ngành phù hợp... PT4; riêng GDMN/GDTC... PT5") có trong nguồn (`aae30:2950–3550`) nhưng không được trích. Verifier nhận nhầm hàng đơn lẻ thành quy luật nhóm.
- Câu 25: câu nguồn bị cắt đúng page-marker (`...quy định của` + `<!-- Trang 3 -->` + `phương thức tương ứng...`, `aae30:5150–5900`). Block kết thúc giữa chừng, khối sau mở đầu chữ thường.
- Câu 62: nguồn CÓ công thức nội suy + chú giải biến + Phụ lục 1/2 (`1610:1800–3000`); đáp án chỉ trích câu mô tả. Formula lines là khối không marker nằm sau mục đánh số "3.".
- Câu 75: toàn nguồn không có URL riêng cho Thông báo 151 (cả 2 tài liệu chỉ có 2 cổng chung `tuyensinh.qnu.edu.vn`, `qnu.edu.vn`); đáp án nói "theo đường dẫn trong thông báo" nhưng không đưa locator.

## Mã thay đổi (7 runtime + 1 test + 1 probe script)

- `backend/app/modules/rag/evidence_audit.py`: `_advisory_missing` (missing tự do mà mọi con số đã trích + số mới không do người dùng nêu → tư vấn, không chặn; thiếu số chưa trích / thiếu không số / số người dùng đã nêu → vẫn chặn) và `_has_checkable_proof` (ref không số/không alias-digit như URL không được auto-retain); auto-retain `retained_by` rỗng cho 3 role số/method khi hợp claims đủ proof, trỏ claim lạ vẫn gap, proof năm giữ nghiêm; `complete` suy lại định danh từ accepted/errors/blocking-missing. `audit_coverage` thêm tham số `question=""` (tương thích ngược).
- `backend/app/modules/rag/evidence_dependencies.py`: `sentence_continuations` (nối câu qua trang: cùng identity nguồn + cùng section + kề thứ tự + khối trước dở câu + khối sau chữ thường, không heading/marker/container, tối đa 2); `_numbered_groups` nhóm mục đánh số với đoạn tiếp nối không marker (dòng công thức, "Trong đó:") và dãy bullet định nghĩa sau dấu hai chấm, tối đa 8 khối; bullet trực tiếp/nhánh chữ cái giữ nguyên tắc cũ.
- `backend/app/modules/rag/evidence_blocks.py`: `pack_context` đóng gói kèm continuations.
- `backend/app/modules/rag/evidence_passages.py`: `source_grounded_claims` gắn continuations như parents (câu cụt luôn có phần nối thành dòng riêng).
- `backend/app/modules/rag/evidence_validation.py`: `group_single_row_gap` (toàn claim `reviewed_fact`, không claim canonical-thực-chất, không hàng trùng thực thể hỏi → trả tên hàng đã chứng minh) và `formula_legend_gap` (hỏi công thức + claim có glyph math U+1D400–U+1D7FF mà anh em cùng nhóm chưa trích → thiếu legend).
- `backend/app/modules/rag/evidence_constraints.py`: `URL_SHAPE` + `location_pointer_gap` (trích dẫn có số hiệu văn bản nhưng không có URL → partial; có URL thì qua; khớp nhãn role `location`/`địa điểm` do planner đặt nhãn tự do).
- `backend/app/modules/rag/evidence_verification.py`: truyền `question` vào audit; áp 3 gap mới (nhóm, locator, legend) thành partial + missing tiếng Việt cụ thể.
- `backend/app/modules/rag/evidence_model.py` + `evidence_indexed_audit.py`: hướng dẫn bổ sung (chọn cả 2 phần câu qua trang; công thức cần khối verbatim + legend + chỉ Phụ lục; hàng đơn chỉ trả lời đúng thực thể đó; where-question phải trích locator; không đòi tổng mới trên các scope riêng trừ khi hỏi rõ).
- `backend/tests/test_evidence_quality_444.py` (mới, 19 ca): advisory/blocking cho missing tự do (4), bù retained cho enumeration + chặn mã thiếu (2), gap nhóm (2) + wiring verify-level (1), nối câu qua trang + chặn heading/hoa/list (2), nhóm formula + legend (1), locator (1) + nhãn tự do (1), auto-retain bỏ qua ref URL (1), sai năm verified-2025-cho-2026 (1). ID câu chỉ trong test.
- `backend/scripts/probe_quality_444.py` (mới): probe 6 câu gốc + 4 paraphrase + 1 đối chứng lịch sử + 1 đối chứng phạm vi, route chat, fingerprint tách fingerprint 443.
- `docs/quy_trinh/03_hybrid_rag_truy_xuat.md`: thêm mục phiên 444 (5 quy tắc).

## Kiểm chứng

- Test-first: 4 lỗi setup test ban đầu (sai block tham chiếu, đảo biến enumerate, reference thiếu mã) đã sửa ở phía test, không đụng runtime; 1 regression thật do thay đổi gây ra (`retained_by` trỏ claim lạ bị auto-retain xóa gap) đã siết lại (chỉ bù khi rỗng) — bằng chứng là suite 437 liên quan báo fail đúng.
- Trọng tâm: 106 pass (`test_evidence_quality_444` 19 + 443/claims/completeness-437/retrieval-regressions). Ruff `app/modules/rag/` + test mới: sạch.
- Full suite cuối: **1275 pass / 11 fail / 15 skip, 0 errors** (~178s, `--basetemp` sang thư mục tạm được phê duyệt do thư mục `pytest-of-AnhTuan` bị khóa ACL — lỗi môi trường, đã xác minh test lẻ vẫn pass khi đổi basetemp; không sửa/xóa thư mục cũ). Đối chiếu từng tên fail với XML 441/443: trùng hệt 11 lỗi nền (consulting 2, cutover/gc 2, decommissioning 3, canary 1, reconciliation 1, trust 1, universal 1), không fail mới.
- Probe thực tế 2 lượt × 12 câu (6 gốc + 4 paraphrase + lịch sử 2025/2026 + phạm vi GDMN), route chat, publication/config `unchanged=true`, fingerprint kho `733f3faf...` giữ nguyên, không timeout hạ tầng (rơi 2 fallback Gemma lẻ là failover bình thường):
  - Lượt 2 (sau toàn bộ vá, `admissions_eval444_probe6_second.json`): 12/12 HTTP 200; 8 supported, 3 partial, 1 missing. Đối soát trích dẫn đọc DB: **30/30 span/hash khớp**, decision integrity 0 lỗi.
  - Câu 6: partial(sai) → **supported ổn định 2 lượt**, giữ scope 53/56 + bổ sung 28/456, không bịa tổng.
  - Câu 9: partial(sai) → **supported ổn định**, đủ PT1–PT5 + 301, trích từng câu.
  - Câu 25: hết cụt ("...nhân hệ số hai." + dòng nối qua trang cùng citations), supported ổn định 2 lượt + paraphrase.
  - Câu 62: lần đầu supported nhưng thiếu legend → sau vá legend-gap thành **partial trung thực** ("thiếu chú giải biến và điều kiện áp dụng"), công thức đã được trích (trước 443 còn không có); legend đã vào context nhưng model chưa chọn trích.
  - Câu 75 (+paraphrase): supported rỗng → **partial ổn định** ("chưa có đường dẫn hoặc địa chỉ cụ thể được trích dẫn"); không bịa URL, không lấy cổng chung đắp vào (qualifier ghép cổng khác scope bị chặn auto-retain đúng).
  - Đối chứng lịch sử (điểm chuẩn 2025→2026) và paraphrase nhóm 1013 ("Một số ngành... PT4", giữ nguyên "một số"): supported đúng phạm vi.
- Điểm chưa giải quyết, không che giấu:
  1. Câu 13 gốc còn dao động giữa các lượt (partial chính sách nhóm + thiếu mã PT4 → missing): guard chặn hàng-đơn-lẻ suy rộng vẫn đứng (không còn supported sai phạm vi), nhưng chọn bằng chứng của model chưa ổn định; paraphrase 1013 và đối chứng GDMN 1113 đều đúng phạm vi. Cần vòng tiếp theo (ưu tiên câu method-identity cho câu hỏi eligibility) trước khi tuyên bố ổn.
  2. Legend công thức mới chỉ vào context, model chưa trích ổn định → Q62 giữ partial trung thực.
  3. Chưa chạy full 82 câu, chưa đo TM-08; không tuyên bố accuracy hay "đã ổn hoàn toàn".

## Bài học

- Planner đặt nhãn intent tự do (`location`/`tìm địa điểm đăng ký`/`registration_location`): gate runtime phải khớp chuỗi role ổn định, không khớp nhãn nguyên văn.
- Auto-retain số học phải từ chối proof rỗng (URL/prose không số), nếu không sẽ xóa gap thật qua tập con rỗng.
- `retained_by` rỗng (model bỏ abstain) khác `retained_by` trỏ claim lạ (model lỗi): chỉ được bù trường hợp thứ nhất.
- Windows: thư mục `Temp\pytest-of-AnhTuan` bị khóa ACL gây 38 errors giả; dùng `--basetemp` sang thư mục tạm được phê duyệt, không đụng thư mục cũ.
