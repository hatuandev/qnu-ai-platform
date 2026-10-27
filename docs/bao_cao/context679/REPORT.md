# Context679 — Hoàn thiện bốn đợt frontend

Đã triển khai sao lưu bằng chứng, dọn blob dẫn xuất, xem nguồn tìm kiếm và đánh
giá truy xuất trên `frontendV1`, nối API `backendV1` có sẵn. Người dùng đã cho
phép triển khai cả bốn đợt. Không thay đổi BE, auth/bypass, ModelOps, provider,
design tokens, cấu hình phục vụ hay corpus.

## Kết quả

| Đợt | Giao diện và hành vi |
|---|---|
| Sao lưu | Vận hành → Sao lưu; tạo với thời hạn/null lâu dài, phân trang server, chi tiết/polling, verify/download ZIP, xóa hết hạn với reason/preview/ack, biên nhận URL. Tạo lại sau mất mạng giữ nguyên body/key; giao worker chưa là xóa xong. |
| Dọn tệp | Vận hành → Dọn tệp; tuổi ≥24 giờ, lý do, danh sách/số tệp/byte, xác nhận riêng, hash/key giữ khi retry, stale phải preview lại, receipt pending tiếp tục sau reload. Giữ nguyên/raw và phân biệt deleted/absent. |
| Xem nguồn | Toàn văn/bảng, spans/notes/unknown, metadata/citations; kiểm lại active publication đúng version/decision trước mở nội dung; liên kết version và OCR revision/run/page đúng scope; skipped reasons và rank trace. |
| Đánh giá | Trang collection/evaluations có deep link run, phân trang snapshot; 1–20 câu, gán nhãn bằng chọn đoạn từ search cùng manifest, label draft/human acknowledgement, dense/hybrid/rerank qua ModelOps, báo cáo từng câu/tổng hợp, xuất JSON/CSV. |

[Hướng dẫn sử dụng](../../quy_trinh/35_frontend_sao_luu_don_tep_va_danh_gia_rag.md).

Baseline796 tệp nguồn/test:10 tệp cũ đổi,22 tệp mới; không mất tệp. Mã BE/auth/
ModelOps giữ hash. `routeTree.gen.ts` được plugin tự sinh, không sửa tay.

Không thêm package/framework. Server state dùng Query, form dùng TanStack Form,
route/search dùng Router/Zod, UI dùng primitives hiện hữu. Cache và tác vụ muộn
được ghim session/workspace/collection. Thêm đúng domain evaluation vào boundary
allowlist; các assertion chặn KTX và persistence token được giữ nguyên.

## Kiểm chứng

Chi tiết lệnh/exit/count ở [verification.json](verification.json). CWD `frontendV1`.
Artifact tổng hợp nằm ở `storage/artifacts/context679-fe-maintenance-evaluation`
(ignored, không có credential/corpus thật).

| Gate | Kết quả |
|---|---|
| Hai tệp test mới | PASS 43 / FAIL 0 / SKIP 0 |
| Regression cùng index-scope677 | PASS 51 / FAIL 0 / SKIP 0 |
| Full FE | PASS 287 / FAIL 0 / SKIP 0; giữ 244 ID cũ + 43 mới |
| Biome toàn FE | PASS 542 tệp, 0 error / 0 warning / 0 info |
| TypeScript và production build | PASS; script build gồm `vite build && tsc --noEmit` |
| Probe độc lập674/676 | PASS 11 và PASS 8 |
| Bundle/template sau build | PASS 11; bridge/bí mật server vẫn bị chặn |
| Sau chỉnh nhãn trạng thái vận hành cuối | Chạy regression UI và build/lint lại; kết quả ở verification |
| Browser | 10 ảnh sáng/tối, desktop và viewport390×844; CSV/JSON tải xuống thật từ fixture |
| Hash/encoding/docs | Đối chiếu baseline và UTF-8 không BOM/LF; xem verification |

Test mới đi qua component và v1 client thật, chặn port bằng HTTP tổng hợp:
age/budget/ack, retry body/hash/key, stale/expired/empty, 403, pending sau remount,
logout/response muộn, role trước đọc dữ liệu, verify hỏng, publication thu hồi/
thay thế, table spans/unknown, snapshot mismatch, gold ID chọn được, human label
ack reset khi sửa, rerank catalog ID, cap20, CSV formula escaping.

Trong quá trình triển khai: build đầu phát hiện field catalog sai, link thiếu
search và pagination thiếu callback; đã sửa. Full lượt đầu FAIL8 do link mới
đặt trong IndexPanel cần router; chuyển link về trang collection vốn sở hữu
điều hướng. Lượt sau FAIL4 do fallback tên đoạn lặp nguyên văn ở cả heading và
snippet; đổi fallback sang tên tệp/nhãn loại, không suy tên từ đoạn văn. Giữ nguyên
các test/assertion cũ. Full cuối đạt287. Hai warning assertion trong test mới đã
sửa, Biome cuối không warning. Không dùng test skip hoặc sửa code để giả kết quả.

## Hình ảnh và xuất tệp

Component/CSS thật được render trên fixture loopback riêng, auth/role/API tổng
hợp, không nối BE/SSO/model thật. Đã kiểm tra overflow tên tệp dài và sửa nút
OCR xuống dòng; ngăn nguồn mobile scrollWidth=clientWidth389, desktop670; báo
cáo mobile390. Nút đóng không chồng tiêu đề. Viewport đã reset; tab/helper đã đóng.

- [Sao lưu desktop](../../../storage/artifacts/context679-fe-maintenance-evaluation/backups-desktop-light.png), [mobile tối](../../../storage/artifacts/context679-fe-maintenance-evaluation/backups-mobile-dark.png).
- [Dọn tệp desktop](../../../storage/artifacts/context679-fe-maintenance-evaluation/cleanup-desktop-light.png), [mobile tối](../../../storage/artifacts/context679-fe-maintenance-evaluation/cleanup-mobile-dark.png).
- [Nguồn desktop tối](../../../storage/artifacts/context679-fe-maintenance-evaluation/source-desktop-dark.png), [mobile sáng](../../../storage/artifacts/context679-fe-maintenance-evaluation/source-mobile-light.png).
- [Đánh giá desktop](../../../storage/artifacts/context679-fe-maintenance-evaluation/evaluation-desktop-light.png), [mobile tối](../../../storage/artifacts/context679-fe-maintenance-evaluation/evaluation-mobile-dark.png).
- [Báo cáo desktop](../../../storage/artifacts/context679-fe-maintenance-evaluation/report-desktop-light.png), [mobile tối](../../../storage/artifacts/context679-fe-maintenance-evaluation/report-mobile-dark.png).
- Hai tệp tải qua nút thật trong browser đã chuyển từ Downloads vào artifact:
  `browser-export.csv` có BOM, `browser-export.json` có request/result.

Các ảnh và số đo tổng hợp chỉ kiểm UI, không chứng minh retrieval/model tốt lên.
Chưa kiểm toàn bộ ma trận bàn phím/trình duyệt/thiết bị hoặc luồng deployment.

## Giới hạn có chủ đích

- NOT RUN: live BE/SSO/worker/storage/model/corpus; tạo/xóa dữ liệu thật, benchmark
  nhãn người dùng, khôi phục DB. Không migrate/reindex/restart/deploy/Git push.
- Backup bằng chứng không phải disaster-recovery toàn hệ thống; restore vẫn CLI.
- Cleanup là xem trước/xác nhận tường minh, không tự bật cron hoặc purge nguồn.
- Gold picker tối đa50 ứng viên/lượt, cần kiểm tính đầy đủ; không suy scope/năm.
  Snapshot và gold còn phải được server kiểm lại. Chỉ snapshot active được đo.
- Chưa lưu lịch sử evaluation trên server vì BE chỉ có POST run. Xuất báo cáo
  phiên hiện tại; chất lượng câu trả lời vẫn NOT RUN, publication approval=false.
- Build còn cảnh báo chunk >500kB có từ trước; không mở rộng tối ưu bundle ở đợt này.
