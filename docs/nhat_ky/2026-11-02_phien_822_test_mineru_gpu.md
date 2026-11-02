# Phiên 822 — So tốc độ MinerU sau khi người dùng chuyển sang GPU

## Phạm vi và phương pháp

User báo đã triển khai MinerU trên GPU, yêu cầu kiểm tra có nhanh hơn không.
Áp dụng skill knowledge-ingestion. Giữ nguyên mã ứng dụng, ModelOps, bản OCR đã
sửa, compiler, publication và index. Không dùng cleanup/init E2E hoặc restart app.

Gửi lại đúng hai PDF đã thử ở816/817, kiểm SHA256 và số trang trước/sau upload:

- Quy chế363,32trang: `59444d277a5e904808537ce70544c1fc83c0bf0a2f2653b78af362af59d5cccc`.
- Quyết định2699,29trang: `84a19db7fcb5e20bf13092088639eecd22cf955169021335d0b56e4bf8e41d77`.

Cùng API đã được chỉ định, tier standard, ocr_mode auto, output default, gửi tuần
tự theo thứ tự363rồi2699. Mỗi file đúng1create/1upload, không retry inference.
Credential đọc riêng từ tệp REST-client đã được phép; không đưa key vào log/docs.
Không tải/lưu corpus vào Git. Serverhealth HTTP200,version4.1.3; health/artifact
không nêu device/cuda/cachehit nên GPU là thông tin do user cung cấp, chưa được
API chứng thực. Không đo tảiGPU,khởiđộnglạnh/nóng hoặc tranh chấp với modelkhác.

Thời gian so sánh cùng ranh giới: từ trước create đến quan sát completed,
bao gồm upload/queue/poll, chưa tính tải ZIP. Không dùng thời gian Nemotron khác
pipeline để xếp hạng tốc độ. Giữ receipt/parser duration riêng.

## Tốc độ thực đo

| File | Lượt cũ | Lượt mới | Nhanh hơn quan sát |
|---|---:|---:|---:|
| Quy chế363,32trang | 906,47s (15phút06s) | 131,00s (2phút11s) | 6,92lần |
| Quyết định2699,29trang | 1663,89s (27phút44s) | 13,14s | 126,63lần |

Parser reported:363từ897.753msxuống115.390ms;2699từ1.654.583msxuống8.242ms.
Cả hai vẫn báo parser4.1.3. Thứ tự lượt thử không đổi;2699chạy sau363,có thể
hưởng lợi từ model đãnạp hoặc cache nhưng không có telemetry để kết luận.
Các hệ số trên mô tả hai lượt cụ thể, không bảo đảm mọi file đều nhanh tương tự.

## Kiểm chứng đầu ra và chất lượng

- Completed32/32và29/29; không trang rỗng, is_full_document=true. Trangidxduynhất
  đủ thứ tự. Sourcehash trước/saukhớp. Tổng61trang.
- ZIP363:12file,409blocks,409bboxhợp lệ hình thức,9ảnhthamchiếutồn tại.
  ZIP2699:31file,104blocks,104bboxhợp lệ hình thức,28ảnhthamchiếutồn tại.
  Toàn bộ artifact đã đối chiếu SHA256, không chỉ tin statuscompleted.
- Chấm lại cùng gold ảnh nguồn đã đóng băng ở816/817, cùng thuật toán căn chỉnh
  cùng trang, giữ dấu tiếng Việt, không sửa chính tả. Gold do trợ lý chép,
  chưa có chấm độc lập; CER/WER chỉ trên mẫu, không đại diện toàn61trang.

| Mẫu | CER cũ → mới | Lỗi ký tự | WER cũ → mới | Probe cũ → mới |
|---|---|---|---|---|
| 363:755từ/3449ký tự,14đoạn/10trang | 0,145% → 0,174% | 5 → 6 | 0,795% → 0,927% | 14/16 → 15/16 |
| 2699:664từ/3053ký tự,20đoạn/13trang | 0,229% → 0,262% | 7 → 8 | 1,054% → 1,205% | 22/22 → 22/22 |

- 363vẫn8bảng; bảngtrang32giữ4hàng×8cột,29ôtrống giốnglượtcũ.
- 2699vẫn26bảngđều8cột; sốhàng4mẫutrang10/19/20/29khớp4/8/7/3.
  Probe text-cùng-hàng đạt4/5so5/5trước. ProbeT02trang19khôngkhớpanchorchínhxác
  vì khác1ký tự; hàng gần nhất vẫn đủ các giátrịmongđợi. Đây là chẩn đoán,
  không đổi criterion hoặc promote probe sai thành PASS.
- Nội dung chuẩn hóa trùng hoàn toàn11/32trang và9/29trang so lượtcũ, nên không
  xem đâylà replaybyte-identical. Không có telemetrycachehit; không suyserver
  đã/không dùngcache từ việc haioutputkhácnhau.
- Mẫu mới thêm1lỗikýtựmỗifile; chấtlượnggầntươngđương nhưng không thể nói chínhxác
  hơnhoặckhôngcònlỗi. Chưa ràsoáttoànbộvùngký/con dấu/ôbảng/nốitrang; các cảnhbáo
  bố cục ở816vẫn là điểm cần đối chiếu, không tựcoiđãsửa.

## Lệnh, kết quả và artifact

- `backendV1/.venv/Scripts/python.exe tmp/mineru822/run.py`: exit0;
  HTTPhealth200,create202,upload200,status200,download200cho cả2file.
- `backendV1/.venv/Scripts/python.exe tmp/mineru822/compare.py`: exit0,
  đủtrang/hash/ảnh/bbox và chấm mẫuđãđóngbăng. Không có ngưỡng gold để gọi chất
  lượng toàn file PASS. Bốn selfcheck nhỏ của scorerđạt; không inference lại.
- Một lệnh đọc chẩn đoán gặp consolecp1252 khi in tiếngViệt; chạy lại chẩn đoán
  với outputASCIIescape, không tạo task hoặc upload lại.

Artifact riêng: `tmp/mineru822/REPORT.md`,plan/health/summary/comparison/diagnostics,
progress,dispatch/latest,twoZIP,Markdown vàJSONgốc,passages/probes/tables từngfile.
Giữ gold cũ nguyênvẹn. Không appbuild/Pytest vì không đổi ứng dụng hoặc evaluator
chínhthức; không commit/push/deploy/đổiOCRmặcđịnh.

Kết luận có phạm vi: triển khai hiện tại nhanh hơn rõ rệt trên hai file đã đo;
chấtlượngmẫu tươngđương nhưng còn lỗi. Kết quả cho thấy đáng thử tích hợp tiếp,
không thay bước ràsoát/xácnhận nguồn trước compiler.
