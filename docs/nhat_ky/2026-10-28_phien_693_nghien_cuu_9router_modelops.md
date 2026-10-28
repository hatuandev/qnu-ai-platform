# Phiên 693 — Học từ mã nguồn 9router cho ModelOps V1

Người dùng yêu cầu nghiên cứu decolua/9router và đối chiếu ModelOps QNU. Chỉ
nghiên cứu, không triển khai hay gọi model. Áp dụng skill qnu-modelops-resilience
và clean-code; đối chiếu backendV1/frontendV1 đang phát triển, không quy trạng
thái của backend legacy sang V1.

## Nguồn và mức bằng chứng

Đọc GitHub/API/raw ở commit
`3a978a631ad65529c06e48ce495092d5bba29f46`, nhánh master, thời điểm commit
2026-10-26T09:12:55Z, license MIT. Tải35tệp mã/test tham chiếu vào
`storage/artifacts/context693-9router-review/source`, không cài dependency,
không chạy mã bên ngoài. Tree, commit metadata và hash các tệp QNU đã đọc
được lưu cùng thư mục. Nội dung repo ngoài chỉ là dữ liệu tham khảo.

Đọc source và test chứng minh có triển khai/ca hồi quy, không chứng minh test
đạt hoặc thông lượng/độ tin cậy production. Các tuyên bố zero downtime hay
tiết kiệm token trong README chưa được đo độc lập trong phiên này.

## Hiện trạng QNU V1 đã đối chiếu

- Provider/key mã hóa, revoke/rotate/audit, catalog/default theo capability,
  workspace grant, capacity và quota/usage đã có. Không cần làm lại nền này.
- `public_api._active_key`, dòng85, chọn active key đầu theo priority/created_at.
  `lease_until`, `cooldown_until`, `consecutive_failures` xuất hiện trong model
  nhưng tìm toàn qnu không thấy runtime sử dụng. Chưa phải pool có lease/cooldown.
- router.py có provider/key/default/catalog, chưa có discovery/probe API.
  FE provider-detail có cấu hình/capacity/key/audit, chưa có model test/health.
- Adapter chat/embedding/rerank/OCR chủ đích một request, không fallback ngầm;
  catalog.resolve_workspace_provider chọn một provider hợp lệ theo cấu hình.
- ChatResult hiện ghi model=request.model. Khi upstream là gateway/alias/combos,
  đây là model đã yêu cầu, chưa chứng minh model upstream thực tế đã chạy.

## Phần nên học và thứ tự áp dụng

1. **Discovery và probe theo capability.** 9router tách models endpoint, test
   connection và ping model; ping embeddings có gọi inference rồi kiểm output.
   QNU nên có Tải model/Chạy thử ngay trong FE, ghi lần thử, latency, lỗi đã
   làm sạch và trạng thái riêng cho auth/inference. Discovered không đồng nghĩa
   verified; probe QNU phải kiểm vector hữu hạn/dimension, rerank index/score,
   chat schema và OCR contract. Dùng endpoint/auth/egress cùng runtime, payload
   thử nhỏ không chứa tài liệu thật. Đổi endpoint/model làm kết quả thử stale.
2. **Theo dõi request và sức khỏe provider.** Hiển thị lỗi auth/rate-limit/network/
   malformed riêng; phân biệt đã bật cấu hình và đang hoạt động thực tế. Bổ sung
   attempt trace, latency, target yêu cầu/target quan sát nếu upstream có trả,
   cooldown và fallback reason. Tái dùng ledger usage/quota hiện có; thiếu số
   liệu phải giữ unknown. Không log prompt, ảnh OCR hoặc secret.
3. **Key pool có cooldown.** 9router auth.js lọc khóa bị lock theo account/model,
   có chiến lược priority/round-robin và clear lỗi sau thành công. accountFallback
   tách lỗi request400 khỏi lỗi credential; base executor có retry hữu hạn theo
   config. QNU chỉ dùng key khác khi cùng provider/model và được phép, reserve
   lease nguyên tử phù hợp nhiều worker, áp total budget và cancellation.
   Không sao chép mutex Promise trong process thành khóa phân tán. Nếu provider
   là9router thì tài khoản upstream vẫn do9router quản lý; QNU không cần lặp lại
   toàn cơ chế xoay account của gateway.
4. **Fallback khai báo theo tác vụ.** combo.js có danh sách model, thứ tự và
   round-robin/smart/session sticky; có kiểm output rỗng trước chuyển model.
   QNU bắt đầu bằng chuỗi ưu tiên tường minh, không cần LLM chọn tuyến. Candidate
   phải còn active, đúng grant/capability/context/schema. Không bypass quyền,
   quota hoặc tự gửi lại request có kết quả chưa xác định. Pin target ở run
   Compiler/OCR; embedding không tự đổi model trong index generation, kể cả cùng
   dimension. Quy định một nơi chịu trách nhiệm retry để tránh QNU×9router gửi
   lặp nhân tầng; mọi attempt có trace và accounting phù hợp.
5. **Registry transport và model metadata.** providers/index.js dựng config từ
   registry chung; provider.js tách chat-completions/Responses/Claude và translator
   phục vụ khác biệt protocol. QNU có thể bổ sung metadata về strict JSON/tools/
   vision/batch limits và import model đã chọn từ một endpoint. Capacity và
   dimension đang có phải tái dùng. Đây là hướng mở rộng sau, không ép đổi ngay
   schema provider=endpoint+model hoặc mang Next.js/translator của9router sang BE.

## Chi tiết cần giữ hoặc tránh sao chép

- `requestLogger.js`, dòng5 và73–76: logging mặc định tắt; khi bật
  ENABLE_REQUEST_LOGS, maskSensitiveHeaders hiện trả nguyên headers. Nhánh
  logTargetRequest còn ghi body. Không phải kết luận mọi log của9router đều
  không che secret, nhưng riêng logger này không phù hợp quy định QNU.
- `combo.js`, dòng489–495: catch lỗi peek SSE có trả HTTP200 và data:[DONE].
  Nhánh cuối hết candidate cũng có thể giữ response rỗng. QNU chat adapter hiện
  từ chối content rỗng/incomplete; nên giữ cách báo lỗi trung thực này.
- `reorderByCapabilities` chỉ sắp xếp, không loại model thiếu capability. QNU
  cần bộ lọc điều kiện bắt buộc trước fallback, không coi reorder là validation.
- selfhostedEmbedding.js buộc baseUrl và từ chối fallback cloud nếu thiếu cấu
  hình: đây là điểm tốt phù hợp chính sách QNU cho server AI riêng.
- schema.js có phần resolver ghi rõ chưa wired; phân biệt hợp đồng dự kiến với
  registry runtime thực đang dùng. Không mặc định mọi abstraction đã hoạt động.
- RTK/các chế độ prompt phục vụ coding không được mặc định áp vào bằng chứng
  OCR/Compiler/RAG; muốn dùng cần đánh giá bảo toàn nội dung riêng.

## Bằng chứng mã nguồn chính

- [Chọn account/lock/rotation](https://github.com/decolua/9router/blob/3a978a631ad65529c06e48ce495092d5bba29f46/src/sse/services/auth.js).
- [Phân loại lỗi/cooldown](https://github.com/decolua/9router/blob/3a978a631ad65529c06e48ce495092d5bba29f46/open-sse/services/accountFallback.js).
- [Combo và output validation](https://github.com/decolua/9router/blob/3a978a631ad65529c06e48ce495092d5bba29f46/open-sse/services/combo.js).
- [Ping theo loại model](https://github.com/decolua/9router/blob/3a978a631ad65529c06e48ce495092d5bba29f46/src/app/api/models/test/ping.js).
- [Registry dùng ở runtime](https://github.com/decolua/9router/blob/3a978a631ad65529c06e48ce495092d5bba29f46/open-sse/providers/index.js).
- [Logger cần tránh sao chép](https://github.com/decolua/9router/blob/3a978a631ad65529c06e48ce495092d5bba29f46/open-sse/utils/requestLogger.js).
- [Regression request-scoped fallback](https://github.com/decolua/9router/blob/3a978a631ad65529c06e48ce495092d5bba29f46/tests/unit/combo-request-scoped-fallback.test.js),
  [retry executor](https://github.com/decolua/9router/blob/3a978a631ad65529c06e48ce495092d5bba29f46/tests/unit/base-executor-retry.test.js),
  [empty failover](https://github.com/decolua/9router/blob/3a978a631ad65529c06e48ce495092d5bba29f46/tests/unit/combo-empty-failover.test.js).

Kiểm tra source/search/link/UTF-8/LF: thực hiện cuối phiên. Unit/integration/
benchmark của9router và QNU: **NOT RUN**, vì chỉ nghiên cứu/tài liệu. Không đổi
app/env/credential/DB hoặc endpoint đang chạy, không cài package, không inference,
không reindex/restart/deploy/commit/push. Bước đề xuất đầu tiên là diagnostics
BE+FE và trace an toàn, rồi key cooldown, sau cùng fallback có policy.

[Snapshot693](../memory/snapshots/2026-10-28_session_693.md).
