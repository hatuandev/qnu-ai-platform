# Context703 — Review Kho tri thức, thư mục và các trang chi tiết

## Kết luận

**CHANGES REQUESTED.** Có10nhóm lỗi chức năng cần sửa; thêm hai khoảng trống về kiểm chứng và bố cục. Lượt này chỉ review, không sửa mã ứng dụng, schema, config hoặc dữ liệu đang phục vụ. Giữ toàn bộ diff người dùng sau HEAD `cd0b90d6`.

Người dùng đã chạy prompt tổ chức Kho tri thức theo quy trình, thêm thư mục kiểu Explorer và tách trang chi tiết; yêu cầu kiểm tra lại. Áp dụng skill QNU clean-code/backend/frontend và gate chung. Không tạo subagent.

## Các finding chức năng

### F01 — P1: sai hợp đồng component làm build thất bại và sai thao tác sửa

`frontendV1/src/features/knowledge/collection-detail-page.tsx:1038` truyền `collectionToEdit`, trong khi CollectionFormDialog chỉ nhận `collection`. Khi chạy dev bỏ qua typecheck, bấm sửa mở form tạo kho mới. Các caller tại collections-panel cũng mắc lỗi này. Callback `onSuccess` tạo kho được truyền nhưng component không nhận/gọi, nên luồng tạo kho trong upload không chuyển đúng kho mới như thiết kế.

Các lỗi cùng đợt: truyền `role?.kind` thay vì object role vào LifecycleActions; truyền `pageIndex/totalItems` thay cho `page/total` vào DataTablePagination; OCR page thiếu import Card và truyền sai `open/onOpenChange` cho CompilationDialog vốn nhận `isOpen/onClose`, thiếu generation của bản OCR. Biên soạn không thể mở đúng từ nút mới. Tổng typecheck **27error**, exit2; Vite có emit assets nhưng toàn lệnh build không đạt.

Sửa caller theo contract thật, không dùng cast/any hoặc nới type để che lỗi. Sau đó kiểm tra sửa kho, phân trang, lifecycle và nút chuyển sang biên soạn bằng hành vi.

### F02 — P1: route OCR con không được render

`frontendV1/src/routes/workspaces.$workspaceId.collections.$collectionId.sources.$sourceId.tsx:27` chỉ render SourceDetailPage, không có Outlet. Route mới `...sources.$sourceId.ocr.tsx` được router generator gắn làm con của route tài liệu này. Vì vậy URL đổi sang `/ocr` nhưng nội dung vẫn là trang tài liệu, OcrReviewPage không mount.

Probe dùng hai file route thật và memory router, stub nội dung hai page, xác nhận OCR leaf không xuất hiện. Tách layout/index hoặc điều chỉnh quan hệ route đúng cách, giữ deep link và nguyên tắc một trang một nhiệm vụ; không chèn cả hai màn đầy đủ lên nhau.

### F03 — P1: xóa thư mục không đưa tệp bên trong vào thùng rác

`backendV1/qnu/domains/knowledge/folders/service.py:342` chỉ ghi ResourceState cho folder IDs. Tệp bên trong vẫn active, vẫn xuất hiện qua `sources?all_folders=true`. UI FolderDeleteDialog lại khẳng định toàn bộ thư mục con và tài liệu bên trong sẽ được đưa vào thùng rác.

Probe API tạo thư mục +PDF giả, xóa thư mục, GET tất cả tài liệu vẫn nhận tệp đó. Cần nối vòng đời nguồn và phạm vi ảnh hưởng/approval/audit phù hợp hoặc làm rõ một hành vi khác đã được người dùng chấp nhận; không giữ thông báo sai. Không hard-delete bằng CASCADE để sửa.

### F04 — P1: khôi phục thư mục thiếu cây con và kiểm tra xung đột

`backendV1/qnu/domains/knowledge/folders/service.py:373` chỉ đổi trạng thái một folder sang active. Xóa cha có con rồi khôi phục cha: con vẫn deleted. Xóa A, tạo A mới cùng vị trí rồi restore A cũ: API200, có hai sibling trùng tên.

Hai probe API đều FAIL. Cần khôi phục đúng nhóm đã bị ảnh hưởng của lần xóa, kiểm tra cha khả dụng và xung đột sibling; không tự khôi phục các tài nguyên vốn bị xóa độc lập trước đó. Trên FE mới chỉ có định nghĩa useRestoreFolder; chưa thấy caller/màn khôi phục folder, lifecycle ResourceKind cũng chưa nhận folder, nên vòng thùng rác trên UI chưa hoàn chỉnh.

### F05 — P1: folder bypass trạng thái kho đã lưu trữ/xóa

`backendV1/qnu/domains/knowledge/folders/service.py:389` lọc scope và trạng thái folder nhưng không load_collection/require_available cho kho cha. update/move/delete/get sử dụng helper này, restore cũng bỏ kiểm trạng thái kho. Scope workspace/role vẫn được kiểm, nhưng lifecycle của kho bị vượt qua.

Probe lưu trạng thái collection=archived như lifecycle đang dùng: đọc kho404, PATCH đổi tên folder bên trong vẫn200. Cần kiểm cha ở mọi handler/service liên quan, kể cả restore; không chỉ ở create/list.

### F06 — P1: idempotency upload không ràng buộc thư mục đích

`backendV1/qnu/domains/knowledge/sources/service.py:123` request hash không chứa folder_id và replay chạy trước kiểm thư mục. Upload cùng file/title/key vào A rồi retry yêu cầu vào B trả200 với file vẫn ở A, thay vì báo request đã đổi. Folder mới trở thành một phần có ý nghĩa của thao tác upload nhưng chưa được đưa vào danh tính request.

Probe API xác nhận HTTP200 và actual folder A khác requested B. Bổ sung folder vào identity, có kế hoạch giữ tương thích replay cũ và validation/availability tương ứng.

### F07 — P1: đưa file vào thư mục làm bộ chọn Compiler không thấy nguồn

`backendV1/qnu/domains/knowledge/sources/service.py:240` đổi mặc định API list sources sang chỉ lấy folder gốc. `frontendV1/src/features/knowledge/compilation-dialog.tsx:103` vẫn gọi useSourcesQuery với page/pageSize, không allFolders hoặc bộ chọn thư mục. Tài liệu đặt trong thư mục biến mất khỏi bộ chọn nguồn biên soạn.

Probe theo đúng request của bộ chọn `/sources?page=1&page_size=100` trả mảng rỗng khi kho chỉ có file trong thư mục. Cần kiểm mọi caller của API cũ; Explorer có thể gửi root tường minh, còn bộ chọn phải lấy/phân trang đúng phạm vi toàn kho hoặc có điều hướng thư mục thật.

### F08 — P2: vị trí thư mục không nằm trong URL

`frontendV1/src/features/knowledge/collection-detail-page.tsx:135` giữ currentFolderId/allFoldersActive chỉ bằng useState. Chọn thư mục chỉ set state và đổi page; schema search của route không nhận thư mục. F5, mở lại link hoặc quay về kho từ trang tài liệu sẽ trở về gốc. Upload sau đó có thể vào gốc thay vì vị trí người dùng nghĩ đang xem.

Đưa folder/view/filter cần giữ vào URL và dùng cùng nguồn cho breadcrumb, truy vấn và upload. Chặn/hiển thị lỗi folder không còn khả dụng; không im lặng thay phạm vi.

### F09 — P1: tải bản gốc từ Explorer dùng số phiên bản thay vì ID

`frontendV1/src/features/knowledge/collection-detail-page.tsx:251` truyền String(source.current_revision_no) vào downloadSourceRevision. Endpoint `/revisions/{revision_id}/content` yêu cầu ID của KBSourceRevision, không phải số1/2/3.

Probe cùng một tệp: dùng revision.id nhận200, dùng current_revision_no nhận404. Trang chi tiết tài liệu dùng ID đúng, nhưng thao tác tải trực tiếp từ danh sách mới bị hỏng. Phân giải đúng ID revision cần tải và giữ chính sách bản đang phục vụ/bản mới rõ ràng.

### F10 — P2: đổi kho đích làm mất file và tiêu đề đang nhập

`frontendV1/src/features/knowledge/source-upload-dialog.tsx:89` effect reset file/title/idempotency chạy lại khi selectedCollectionId hoặc danh sách collections thay đổi. Người dùng chọn file và nhập tiêu đề, sau đó đổi kho đích thì dữ liệu form bị xóa. Tạo kho mới và một số lần refetch cũng rơi vào nhánh này.

Probe component thật với hook dữ liệu giả: tiêu đề “Keep my title” trở thành chuỗi rỗng ngay sau chọn B. Tách reset lúc mở phiên upload mới khỏi đổi đích/refetch. Khi đổi ý nghĩa request cần key mới nhưng vẫn giữ file/title để người dùng quyết định tiếp.

## Khoảng trống bổ sung

- **Kiểm chứng chưa nối schema mới:** integration fixture TABLES thiếu kb_folders, khiến TRUNCATE kb_collections bị FK chặn trước khi test chạy. Tái hiện ca `test_changed_title_is_a_different_idempotent_request`:1ERROR. Test schema vẫn đòi head0005 trong khi DB đã0006:1FAIL. Test mới của prompt chỉ kiểm validation/schema, chưa kiểm API/tree/delete/restore. Phải sửa hạ tầng test và bổ sung regression; không coi411test FE cũ là nghiệm thu feature mới.
- **Bố cục còn nhiều ngữ cảnh trên cùng trang:** browser desktop thấy header quản trị workspace, nút sửa/tạm dừng và10mục workspace phía trên trang Kho tri thức, ngoài sidebar. Nút tải lên đã dễ tìm hơn và khối “Đang làm việc” đã bỏ, nhưng màn hình chưa đạt hoàn toàn yêu cầu ít rối. Nên thu gọn workspace shell của các trang nghiệp vụ và đặt quản trị workspace ở trang chi tiết riêng.

## Lệnh và kết quả thực chạy

Cwd root repo cho BE và script; `frontendV1` cho npm. Không gọi model thật.

| Kiểm tra | Kết quả |
| --- | --- |
| `npm run build` | FAIL: Vite emit thành công, tsc27error. Shell wrapper ban đầu đọc log nên exit shell0; không dùng exit đó để báo build PASS |
| `npm run typecheck` | FAIL27error, exit2 |
| `npm test -- --maxWorkers=2` | 411PASS/44file, exit0; bộ cũ không có case mới |
| Review FE `review-703-temp.test.tsx` | 2FAIL: form reset và OCR route, không sửa assertion/app để làm xanh |
| Scoped Ruff | PASS15file, exit0 |
| Scoped Biome | FAIL19file, exit1; chi tiết trong artifact log |
| Review BE +unit folder +schema | 7PASS/6FAIL, exit1, DB `qnu_v1_test_a645c3f1f4fd4dd1` dọn |
| Probe bộ chọn nguồn mặc định | 1FAIL, exit1, DB `qnu_v1_test_cdd23d10458944ef` dọn |
| Regression integration cũ với fixture nguyên bản | 1ERROR do thiếu kb_folders, exit1, DB `qnu_v1_test_b818ed3213184b37` dọn |
| Full BE | NOT RUN: fixture đang lỗi ở bước thiết lập đã tái hiện; không sửa fixture để che rồi tuyên bố suite đạt |

Các probe BE có fixture cục bộ thêm kb_folders vào TRUNCATE để đi tới handler; không sửa fixture chung. Test fixture nguyên bản chạy riêng và báo ERROR rõ ràng. Tổng probe handler8case:6FAIL/2PASS; unit folder5PASS; schema1FAIL. Hai ca handler PASS kiểm scope/role/cycle và chứng minh endpoint revision ID khác revision number.

Harness tạo DB test loopback, môi trường con tối thiểu, không sao chép credential/corpus và chặn network ngoài. Cả ba receipt xác nhận db_dropped=true, legacy_sentinel_preserved=true. Nguồn probe, logs và hashes ở `storage/artifacts/context703-knowledge-review/`, không đưa corpus/secret vào docs.

Browser chỉ đọc landing và mở/đóng dialog upload trên FE3001 hiện có; không tạo kho/thư mục, không upload, không sửa dữ liệu hoặc restart. Landing đang trống nên chưa kiểm visual Explorer có cây dữ liệu, mobile/dark và toàn luồng OCR/Compiler thật. Tab review riêng đã đóng.

Temporary probe ở tests đã xóa sau đối chiếu bytes với bản artifact. Mã ứng dụng và test của người dùng giữ nguyên. Chỉ thêm nhật ký/snapshot và index/memory của review; chưa triển khai fix hoặc áp migration lên DB đang phục vụ.
