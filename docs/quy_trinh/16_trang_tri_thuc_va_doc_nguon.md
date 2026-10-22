# Trang tri thức và đọc nguồn có giới hạn

## Luồng sử dụng

DOCX/PDF mới được chuẩn hóa thành cặp QNU Markdown/Structured JSON, qua Quality
Gate và tạo tập nội dung dẫn xuất. ModelOps chọn nội dung cho trang tri thức khi
tạo chunk set, trước bước embedding; server dựng thân trang từ nguyên văn nguồn.
Trang xuất hiện ở **Nội dung → Trang tri thức**.
Chọn **Xem trang**, mở trang nguồn/đối tượng/chủ đề và bấm **Xem nguồn** để đối chiếu.

Nguồn cũ và các chỉ mục đã dựng không tự biên soạn lại. Để áp dụng cho nguồn cũ,
cần tạo revision mới và nạp vector trong một thao tác được người vận hành cho phép.
Tạo trang hay embeddings không tự xuất bản tài liệu.

## Biên soạn

- Chính sách phiên bản `qnu-knowledge-wiki/v1`, ghi trong provenance của revision
  DOCX/PDF mới. Không thay đổi Markdown, JSON, facts hay annotation đã duyệt.
- Revision mới dùng compiler `qnu-wiki-compiler/v3`, chế độ `extractive` theo lựa
  chọn của người dùng: LLM phân tích và chọn trang/source-unit IDs; server dựng
  trích đoạn nguyên văn cùng heading, header và các liên kết context bắt buộc.
  Trang nguồn giữ đủ danh mục unit không phải container; trang thực thể/khái niệm
  là nội dung được chọn, không phải bản tổng hợp đầy đủ mọi quan hệ.
  Model không viết lại số liệu, mã, ký hiệu, điều kiện hoặc ngoại lệ trong thân trang.
  Mỗi gói thường chỉ cần một lượt chọn; retry hợp đồng nằm trong ngân sách tổng.
  Khi đọc lại, server dựng lại trích đoạn từ canonical để kiểm text và tập refs,
  không chỉ so hash. Thiếu header/context hoặc vượt sức chứa thì chặn, không cắt.
- Compiler v2 và policy cũ không có render_mode giữ chế độ `generated` tương
  thích. Với chế độ cũ, lượt một phân tích, chọn trang và source-unit IDs. Lượt hai sinh các phần nội
  dung, chọn ID bằng chứng cho từng phần và phạm vi năm; server gắn nguyên văn
  `unit.text`, giữ cả ngắt dòng. Không yêu cầu model chép lại trích đoạn. ID phải
  thuộc outline của đúng trang; quote object từ caller cũ vẫn được kiểm nguyên
  trạng, không tự sửa thành quote hợp lệ. Trang nguồn luôn có; trang thực thể
  và khái niệm được tạo khi có nội dung đủ căn cứ, không tạo đối tượng giả cho đủ số.
- Request dùng handle ngắn `u0`, `u1`… do server cấp riêng cho từng gói. Hợp đồng
  ràng buộc kind/title và tập handle của từng trang theo outline. Server chuyển
  về ID canonical trước lưu; handle không trở thành ID nguồn hoặc citation.
  Mỗi phần nhận tối đa 20 tham chiếu, cùng giới hạn với hợp đồng trang đã lưu.
- Mỗi phần giữ riêng năm dữ liệu, năm ban hành, hiệu lực và sự kiện. Unknown giữ
  unknown. Năm chỉ có trong tên tệp không đủ chứng minh phạm vi dữ liệu.
- Gói dài mang lại heading cha nguyên văn khi sang gói mới. Không cắt đôi source
  unit để vừa ngân sách. Gói quá lớn trả trạng thái không biên soạn được; nguồn
  vẫn phải tuân Quality Gate riêng của nó.
- Dòng bảng mang theo các liên kết `context_refs`/`field_context_refs` đã có trong
  canonical, gồm header. Packet và outline đóng các phụ thuộc này, giữ thứ tự
  nguồn; heading trùng tên dùng instance đứng trước unit. Thiếu liên kết nguồn
  thì chặn, không tự tạo header hoặc gắn chú thích khác bằng từ khóa.
- Kiểm tra JSON, tập trang, IDs, trích đoạn, số/mã, chứng cứ năm và hash trước lưu.
  Đây là kiểm tra toàn vẹn, **không phải phê duyệt quan hệ ngữ nghĩa**. Nhãn năm do
  LLM đề xuất chỉ hỗ trợ điều hướng; đáp án cuối vẫn phải qua đối soát nguồn.
- Kết quả lưu cùng chunk set, được ghim vào index revision và hash bundle dẫn
  xuất; dùng lại khi dựng generation khác. Nguồn đổi tạo trang mới, không chồng
  nội dung khác revision vào trang đang phục vụ.
- Model/provider chính và fallback lấy từ ModelOps DB hiện hành. Không có model
  cố định hoặc API key trong tính năng này. Usage được ghi trong giao dịch riêng.

Compiler `qnu-wiki-compiler/v2` gom heading/temporal giống nhau vào bảng scope
dùng chung; mỗi unit giữ nguyên ID và văn bản, tham chiếu scope bằng ID. Không
bỏ bằng chứng để giảm kích thước. Gói được chia theo toàn request, kể cả chỉ dẫn,
hợp đồng đầu ra, metadata, dàn trang và phần dành cho phản hồi sửa hợp đồng.

Ngân sách mặc định: tối đa 24.000 ký tự nguồn/gói và 180.000 ký tự nguồn cộng dồn,
32 lượt model, 2.500 output tokens/lượt, 600 giây toàn tác vụ. Mỗi request có
ceiling 24.000 gồm phần đầu vào, framing và output reserve; đây là giới hạn công
việc, không phải thông số context window của model. Khi chưa có tokenizer đã
cấu hình, dùng số byte UTF-8 làm cận trên bảo thủ cho tokenizer byte-level cùng
1.024 framing reserve; không báo nó là token quan sát. Token thật từ usage được
ghi riêng. Không áp tỉ lệ ký tự/token trung bình cho tiếng Việt.

Kiểm tra trước mỗi lần gọi, gồm retry, không chỉ trước gói đầu; không cắt source
unit hoặc cắt điều kiện để vừa ngân sách. Mỗi gói chọn tối đa ba trang. Giới hạn
ba phần/trang áp dụng cho đầu ra prose của v2; v3 server giữ từng trích đoạn đầy
đủ, tối đa 512 phần/trang và 20 tham chiếu/phần, không yêu cầu LLM xuất lại text.
Bảng đầy đủ vẫn ở canonical source. Không đổi timeout/model
provider đang chạy khi thay giới hạn công việc này.
Lỗi provider, hợp đồng hoặc budget hiển thị `unavailable`, không ghi trang giả.
Đầu ra sai hợp đồng/bằng chứng được sửa tối đa hai lần trên cùng gói; mỗi lượt
vẫn tính vào giới hạn tổng 32 yêu cầu compiler, ký tự nguồn và thời gian. ModelOps
giữ chính sách retry/fallback provider hiện có; giới hạn compiler không thay nó.
Draft chưa đọc được JSON/shape phải sinh lại. Với draft đã đọc được, server chỉ
cấp đúng section lỗi và outline của trang đó cho bản sửa. Các section đã đạt giữ
nguyên; bản sửa cần exact target coverage, không thiếu/trùng/thêm target. Bản ghép
vẫn qua toàn bộ kiểm tra trước lưu, không phê duyệt từng phần chưa đạt.
Handle giữ nguyên qua retry dù context thu hẹp. Tham chiếu ngoài outline của
draft đánh dấu rõ là không hợp lệ, không chuyển thành bằng chứng được chấp nhận.
Phản hồi gộp các lỗi theo page/section trong ngân sách, gồm ID ngoài phạm vi và
số/mã thiếu chứng cứ; gợi ý ID chỉ lấy từ outline đã cấp, không tự gắn bằng chứng.
JSON sai cú pháp vẫn bị từ chối, chỉ bỏ một lớp code fence bao ngoài hợp lệ;
không trích JSON ra giữa văn bản hoặc chữa nội dung để vượt validator.
Model không được ghép nhiều giá trị thành một chuỗi số mới. Claim thiếu căn cứ
trong outline được bỏ trọn vẹn khỏi trang điều hướng, không giữ kết luận rồi
cắt điều kiện/ngoại lệ. Canonical, JSON và facts nguồn không bị bỏ theo claim đó.
Không retry lỗi quyền/provider theo đường riêng, không nới kiểm tra để chấp nhận.

## Chatbot đọc thêm

Chỉ mục đã xuất bản có trang tri thức bổ sung điều hướng cho câu hỏi diễn giải.
Các câu hỏi fact-first giữ nhánh đối soát ô/hàng hiện có, không chuyển sang trả
lời prose chỉ vì index có trang wiki. Chính sách evidence được cấu hình bật rõ
vẫn có hiệu lực theo cấu hình; wiki không ghi đè lựa chọn đó.
Tìm trang bằng nội dung và tiêu đề, chọn phần phù hợp phạm vi năm. Model chọn
trang; server mở ngay các block canonical mà phần trang đó tham chiếu, rồi bàn
giao cho bước kiểm chứng câu trả lời. Không gọi model thêm một lần chỉ để xác
nhận đã đọc. Khi chưa có trang phù hợp có thể tìm lại trong cùng snapshot hoặc dừng.

Model chỉ gửi IDs do server cấp, không được chọn URL, đường dẫn file, SQL hay công
cụ ghi. Mặc định tối đa hai lượt điều hướng, 14.000 ký tự trang và 30 giây. Nội
dung trang còn phải chia sẻ ngân sách context tổng với bằng chứng gốc. Không reset
số lượt khi corrective retrieval hoặc tham chiếu lịch sử diễn ra trong cùng request.
Lần gọi sai hình dạng có thể sửa trong cùng số lượt còn lại; mọi lần thử đều được
đếm. Lỗi quyền, nguồn hoặc provider không được biến thành retry sửa JSON.

Trang dài được mở theo các phần phù hợp câu hỏi, mỗi phần giữ nguyên toàn bộ
header/context/nguồn. View ghi rõ là một phần của trang và tổng số phần; không
cắt chuỗi giữa điều kiện hoặc giả rằng đã đọc toàn tài liệu. Phần riêng lẻ vượt
ngân sách không được mở bằng cách cắt bỏ chứng cứ.

Các trang mở được đưa vào ngữ cảnh để hỗ trợ tìm nguồn. Bằng chứng có thể
trích dẫn chỉ là block nguyên văn của đúng binding/index/source revision/hash.
Đáp án vẫn qua claim binding, xác minh và kiểm tra điều kiện/ngoại lệ hiện có.
Không tự diễn giải ký hiệu chưa định nghĩa thành 0 hoặc đổi ánh xạ mã phương thức.

Gợi ý wiki không được tự chiếm ưu tiên toàn bộ context. Đoạn được người dùng
chỉ địa chỉ trực tiếp, record đã xác định và nhóm điều kiện nguồn được đóng gói
trước; các danh sách đánh số giữ nguyên nhóm trong ngân sách, không bỏ điều kiện
đầu vào để lấy riêng câu cho phép. Caption đi cùng hàng bảng chỉ chứng minh vị
trí bảng, không tự chứng minh năm dữ liệu. Không đủ ngân sách vẫn phải báo thiếu.

Header bảng và caption vẫn được đưa nguyên văn vào context và tính vào giới hạn
kích thước. Chúng không chiếm thêm suất đoạn nội dung trả lời trong Top-K, tránh
đẩy mất các điều kiện của cùng một quy định. Caption hình/bảng mở một đối tượng
mới, không trở thành phần tiếp nối của danh sách quy định đứng trước nó.

Khi audit phát hiện điều kiện hoặc ngoại lệ bị thiếu, server chỉ bổ sung nguyên
văn đã có trong các block nguồn được cấp, rồi kiểm chứng lại toàn bộ claim.
Tối đa hai vòng bổ sung, dừng khi lặp cùng khoảng hở hoặc vượt ngân sách. Không
bổ sung bằng cách đoán, đổi số liệu, bỏ lỗi scope hay bỏ qua coverage chưa đủ.

Câu hỏi đọc nội dung tài liệu có phạm vi riêng với câu hỏi về hiệu lực hoặc dữ
liệu của một năm. Persona không chứng minh tài liệu thuộc cơ quan nào; không tự
đưa năm mặc định vào câu hỏi chỉ đọc nguồn. Nguồn nhiều năm hoặc phạm vi chưa rõ
vẫn cần kiểm chứng/làm rõ theo yêu cầu thực tế.

Với câu hỏi nối tiếp, bộ lập ngữ cảnh tách `source_locator` (bảng/điều/mục)
và `metric` (đại lượng) khỏi chủ đề chung. Mỗi tham chiếu giữ một giá trị nguyên
văn, một lượt người dùng và đoạn trích chứa đủ giá trị đó. Chỉ ghép các giá trị
đã có căn cứ trong câu hỏi độc lập; câu trả lời cũ của assistant không là căn cứ.
Mã, năm mới nhất, đại lượng hiện tại và phủ định vẫn phải được kiểm lại ở server.

Một đề xuất nối tiếp sai tham chiếu/phạm vi được phép sửa đúng một lần từ cùng
lịch sử người dùng. Hai lượt dùng chung thời hạn 20 giây của bước lập ngữ cảnh;
không reset timeout hoặc nhân thêm retry JSON. Bản sửa đổi mode/intent sang
nhánh khác không được chấp nhận để vượt kiểm tra. Vẫn sai thì hỏi lại, lỗi
provider/quyền hoặc hủy tác vụ không trở thành retry sửa tham chiếu. Đây chỉ là
diễn giải câu hỏi, không chứng minh fact hoặc cấp quyền đọc/ghi nguồn.

Guard Context594 kiểm thêm coverage của tên đối tượng, cơ quan, mã, tài liệu và vị trí
nguồn mà người dùng nêu. Mỗi giá trị kế thừa phải giữ đủ tên và căn cứ đúng lượt;
URL cùng giao thức không chứng minh cùng tài liệu. Role `source` chỉ là định danh
trong câu hỏi, không cấp quyền cho binding/revision hoặc URL ngoài hệ thống.

Điều kiện, đích loại trừ, phủ định và AND/OR được giữ nguyên cụm trong cửa sổ hội thoại.
Không tự bỏ lọc cũ vì đổi đại lượng/năm hoặc chọn antecedent gần hơn. Các cụm từ nhiều
lượt được giữ riêng; toán tử nối mới chưa có căn cứ bị chặn. Lệnh bỏ/thay một điều kiện
phải xác định nguyên cụm cũ; nếu chưa đủ căn cứ thì hỏi lại. Lệnh phủ định hoặc một
câu chỉ trích dẫn lệnh không cho phép bỏ lọc. Khi bỏ lọc đã được kiểm chứng, truy vấn
không nối lại phần điều kiện bị bỏ; original user request vẫn giữ trong provenance.

Legacy rewrite cũng kiểm tên/điều kiện theo literal user text. Đường tắt đổi năm không
bỏ qua lượt user thêm điều kiện mới hơn. Không dùng từ điển tên ngành, mã hay tên tài
liệu của benchmark. Các diễn đạt không chứng minh được, kể cả câu nguồn không rõ,
có thể hỏi lại; chưa coi đây là bộ phân tích ngữ nghĩa hoàn chỉnh cho mọi cách nói.

Một tuyên bố của nguồn được trình bày như heading có thể là nội dung trả lời khi
được chọn trực tiếp cho câu hỏi đọc tài liệu; heading hỗ trợ không thay thế bằng
chứng nội dung khác. Chỉ khi nhánh wiki không tạo được claim nào, câu hỏi rõ là
đọc nguồn và không có conflict hoặc binding rejection, hệ thống mới thử bộ đối
soát canonical hiện có trong phần thời gian còn lại. Không dùng đường này để
che lỗi provider, vượt chính sách evidence được bật hoặc biến partial thành PASS.

Consumer ô mặc định vẫn từ chối trạng thái chưa rõ nghĩa. Nhánh đọc chú giải có
thể dùng catalog ở chế độ mô tả để tìm bằng chứng, nhưng không chọn các ô hạn chế
làm giá trị đã xác minh. Raw/header/span lệch nguồn vẫn là lỗi cứng. Giải thích
bằng chú giải không tự duyệt annotation hoặc thay đổi state đã lưu.

## Ngữ cảnh và ngân sách sau Context595

Bộ phân giải hội thoại kiểm role thời gian riêng: năm học, năm dương lịch, năm dữ liệu,
năm ban hành, năm hiệu lực và năm sự kiện. Cùng chữ số không cho phép đổi role. Khi
so sánh hai chủ thể có năm khác nhau, câu viết lại phải giữ đúng cặp chủ thể/năm;
role của referent cũng được kiểm theo user turn. Không suy ngày hiệu lực từ tên file.

Một role có thể có nhiều referent khi người dùng yêu cầu một tập/so sánh rõ ràng.
Mỗi giá trị vẫn cần quote literal và lượt người dùng. Câu sửa chủ thể không tự giữ
chủ thể cũ. Các vị trí bảng/điều phải gắn đúng tài liệu, không hoán đổi giữa hai nguồn.
Tập hoặc mối liên kết chưa rõ vẫn hỏi lại; schema không mở quyền đọc nguồn.

Sau khi model chọn tối đa ba trang, server chia ngân sách cho đúng các trang đó,
không cắt sẵn mỗi trang còn một phần ba. Chỉ lấy nguyên section và dependency closure;
phần vượt cổng ngân sách được loại nguyên nhóm. Tổng context phải có chỗ cho cả
Markdown điều hướng và canonical evidence; bước packing cuối vẫn kiểm tổng budget.

Cache request giữ selection/nội dung riêng với view hiển thị. Mỗi lần dùng lại phải
đối chiếu snapshot, revision/hash, quote, nội dung block và closure rồi tạo lại view
theo budget và policy hiện hành. Hạ budget không trả nội dung cũ quá dài; tăng budget
không reset bộ đếm lượt gọi model. Mất reference/đổi nguồn không được trả một phần
closure như thể đã đủ. Khi policy tắt, view cache không tiếp tục đi vào prompt.

## Kiểm chứng qua vòng sửa sau Context597

Trong một request, điều kiện mà audit nguồn đã xác định là bắt buộc được giữ trong
bộ nhớ tạm theo câu hỏi/plan, collection và tọa độ nguồn có revision/hash. Vòng sửa
sau không tự xóa điều kiện đó bằng một verdict khác. Điều kiện còn thiếu chỉ được
chép từ đúng block đang có trong ngân sách rồi kiểm chứng lại; mất chứng cứ thì chặn.
Đổi chủ thể/phạm vi hoặc dùng revision khác không kế thừa điều kiện tùy tiện.
Đây không tạo annotation đã duyệt, ghi dữ liệu hoặc mở quyền publication.

Chỉ mệnh đề điều kiện nguồn chính xác được giữ qua các vòng; một đoạn trích làm
chứng cứ cho qualifier không có nghĩa mọi câu trong đoạn phải đưa vào đáp án.
Với phần còn thiếu, bước đọc quan hệ nguồn riêng nhận câu hỏi gốc/body/clause và
không thấy bản nháp hoặc verdict cũ. Các liên kết phải dùng ID hợp lệ trong cùng
nguồn/revision/hash; tối đa hai lượt trong request, có cache nội dung/phạm vi.
Phần đã giữ nguyên với đúng public owner không gọi lại bước này.

Bước đọc quan hệ nhận cả đoạn nguồn đã được server gắn vào câu trả lời để xác định
đúng nhánh đang hỏi. Với câu hỏi về đầu vào thiếu, chỉ yêu cầu điều kiện của nhánh
đó và ngoại lệ có liên quan; không mặc định yêu cầu mọi định nghĩa của nhánh tính
toán thành công. Không dùng nội dung bản nháp làm bằng chứng xác định nhánh.

Mỗi đoạn nguồn được chọn là một đối tượng kiểm tra riêng, kể cả khi nhiều đoạn
nằm trong cùng block. `governs` phải trỏ đến ID trích đoạn ấy; ID của cả block không
thay thế được nó. Nội dung block đầy đủ chỉ nằm trong `source_context` làm nền,
không biến những nhánh chưa chọn thành các khẳng định phải kiểm tra hoặc công khai.

Chỉ trích đoạn canonical có tọa độ hợp lệ mới được dùng làm điều kiện nguồn.
Dữ kiện dẫn xuất không có tọa độ ký tự không trở thành một mệnh đề canonical,
kể cả khi nằm cùng bảng hoặc có nội dung giống nhau. Không thay offset thiếu bằng0.

Vòng chọn lại giữ các claim an toàn trước đó rồi kiểm chứng toàn bộ. Claim không
liên quan đã bị loại không tự ngăn phục hồi điều kiện cho các claim còn hợp lệ.
Fallback quy tắc có thể giữ dòng thô được hỏi dù một cột hạn chế, kèm trạng thái
hạn chế và đúng caption; việc đọc mô tả không cho phép dùng ô đó làm số liệu.

Catalog trích nguyên văn dùng ranh giới câu/mệnh đề có cấu trúc để model chọn phần
vừa đủ, giữ riêng body và supporting context. Các điều kiện/định nghĩa có thể được
bảo toàn qua nhiều claim nếu mọi phần đều có đúng nguồn và span; thiếu một phần vẫn
không đạt. Không suy ý nghĩa từ tập số hoặc bỏ phủ định, năm và ngoại lệ.
Không tách thêm vị từ ngày bên trong native list hoặc dòng bảng.

Referent vẫn cần quote nguyên văn trong user turn. Khi đối chiếu với câu viết lại,
text tự nhiên chấp nhận khác biệt hoa/thường và khoảng trắng; mã và địa chỉ nguồn
vẫn phân biệt hoa/thường. Không thay bằng từ đồng nghĩa hoặc bỏ kiểm vai trò/phạm vi.

Benchmark nghiệm thu chạy tuần tự trong một lượt, không chạy synthetic ModelOps
đồng thời. Giữ nguyên query/rubric/source/model, ghi lỗi hạ tầng thành FAIL và lưu
retry riêng nếu có. Lock của runner ngăn phát lại cùng lượt đã có run-intent; không
thay cơ chế khóa hoặc quota của ModelOps.

## Bổ sung Context599 — Phục hồi ý trả lời và đối chiếu điều kiện mới

Fallback giữ riêng ý trả lời còn thiếu và điều kiện nguồn còn thiếu. Tối đa hai
vòng như trước; bổ sung điều kiện xong vẫn có thể chọn lại nguồn cho ý còn thiếu.
Mỗi vòng dùng kết quả kiểm chứng mới nhất, giữ claim an toàn và kiểm lại toàn bộ.
Nếu đã bổ sung điều kiện mà qualifier vẫn chưa đạt, lượt sau chọn lại bằng chứng
thay vì tiếp tục chỉ chép qualifier; không tăng số vòng hoặc tự công nhận đầy đủ.
Trace phân biệt hoàn tất, mâu thuẫn, không tiến triển, hết budget và verdict chưa
đạt nhưng không còn gap có thể xử lý. Không coi verdict chưa đạt là PASS.

Nếu source-only review đề xuất một điều kiện mới mà indexed audit chưa xác nhận
là bắt buộc, hệ thống đối chiếu độc lập trước khi ghi nghĩa vụ. Payload chỉ có câu
hỏi/plan và nguồn gắn ID, không có bản nháp hoặc verdict trước. Một `clause_id`
được liên kết một lần với `evidence_ids` của các trích đoạn đã xét; server kiểm ID,
liên kết, tính duy nhất và cùng nguồn/revision/hash khi xác nhận bắt buộc. Kết luận
chưa rõ hoặc lỗi hợp đồng vẫn chặn và có mã lỗi kiểm chứng, không báo thiếu nguồn.

Tối đa hai lượt source-only review hiện có và thêm tối đa **một** lượt đối chiếu
điều kiện mới trong request; cache theo nội dung/phạm vi. Ngân sách được ghi trước
khi gọi; trace giữ ID, trạng thái và mã lỗi, không ghi toàn prompt hoặc nội dung
riêng. Quyết định không bắt buộc chỉ áp dụng cho đề xuất mới đang bất đồng, không
xóa nghĩa vụ đã xác nhận qua vòng trước. Ý nghĩa quan hệ vẫn là phán đoán LLM được
kiểm tra cấu trúc, không phải chứng minh ngữ nghĩa tuyệt đối bằng ID.

Một lượt đối chiếu có thể xem các clause ứng viên đang chờ cùng lúc, nhưng chỉ
điều chỉnh đề xuất mới đang bất đồng; không ghi mọi kết luận độc lập thành nghĩa
vụ. Proof theo clause/câu hỏi/plan/nguồn và trích đoạn đích được giữ trong request.
Khi thêm một claim sau repair, chỉ dùng lại proof cho chính target đã xét, có cùng
nội dung, span và nguồn. Đổi question/plan, target hoặc revision không được dùng lại;
đích mới chưa được kiểm mà đã hết budget vẫn chặn. Không xóa hoặc nới ledger cũ.

Audit hàng bảng kiểm nội dung ô trong đúng hàng/phạm vi. Header gắn theo cấu trúc
không tạo thêm một yêu cầu ngoài câu hỏi; phủ định trong ô vẫn phải giữ nguyên.
Không tự cho qua scope, năm, tiền đề hoặc ngoại lệ chỉ vì quote khớp chữ. Gate số
giữ nguyên: số người dùng nhập không trở thành bằng chứng nguồn hoặc kết quả tính.

## Quyền, publication và tương thích

API xem trang dùng quyền `ai.knowledge.view` và exact collection/binding/revision.
GET chỉ đọc, không kích hoạt LLM. API quản trị có thể xem trang trước xuất bản;
chatbot thông thường chỉ đọc index `active` thuộc snapshot đang có hiệu lực.
Candidate chỉ được đọc index `ready` qua luồng kiểm thử có quyền sẵn có.

Không thêm bảng/migration, không đổi default model, không tắt validation hay
Quality Gate, không tự chuyển active pointer. Cơ chế phục vụ nguồn cũ giữ nguyên
khi snapshot chưa có trang tri thức. Chưa có hợp nhất trang thực thể xuyên nguồn
hoặc đồ thị wiki; đó là phạm vi tiếp theo, không thuộc ba ưu tiên đầu.
