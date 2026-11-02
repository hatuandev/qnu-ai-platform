# Phiên 806 — Chốt nhánh v1.0.3 độc lập với FE đang chạy

## Phạm vi được xác nhận

Người dùng yêu cầu đánh giá V1, tạo nhánh v1.0.3 và push; xác nhận lưu mốc phần đã
hoàn tất, để FE đang chạy bổ sung sau. Chỉ dọn cache/tệp tạm chắc chắn không dùng,
giữ báo cáo/OCR và dữ liệu test. Đây là checkpoint phát triển, chưa nghiệm thu
production: lỗi unit716 và chất lượng spelling4/8failed còn được giữ trung thực.

Không chuyển nhánh hoặc stage tại thư mục chính. Tạo worktree riêng
`tmp/release-v1.0.3` từ77dfb99e (Gitea v1.0.2 đã fetch và cùng HEAD), nhánh chính
v1.0.2 tiếp tục để IDE sửa FE. Copy phần BE/OCR800–805, profileLuna/testselection
và tài liệu có hash snapshot; loại các featurefiles/testOCR FE đang sửa.
Không reindex, restart, deploy, đổi key/DB hay gọi model thật.

## Lỗi đóng gói mã nguồn đã khắc phục

Checkout sạch thiếu `qnu.adapters.storage`: backendV1/.gitignore dùng storage/
không neo root, làm bỏ qua cả package adapters/storage. Máy cũ có file nên không
phát hiện ở các lượt test trước. Redcheckout fullPytest24collectionerrors.

Đổi đúng một rule thành /storage/; bổ sung3file mã đã có __init__.py/local.py/s3.py
vào snapshot. Không sửa thuật toán adapter; không đưa runtime storage lên Git.
gitcheck-ignore xác nhận backendV1/storage vẫn bị ignore. Ruff toàn phạm vi mớiPASS.

## Kiểm chứng bản chốt

- Backend sạch sau bổ sung adapter:693PASS/1FAIL/77SKIP,exit1,18.20s.
  ExactID còn lỗi:
  tests/unit/test_source_purge_716.py::test_accept_rechecks_publication_after_preview_before_preparing_purge
  báo invalid_identity401; không sửa quyền/fixture để làm xanh. DB integration
  không bật TEST_DATABASE_URL nên77SKIP, không gọi DBlive.
- Frontend full cuối:73suites/663PASS/0FAIL,exit0,50.89s. Lần đầu657PASS/3FAIL/
  3SKIP do worktree chưa có đường dẫn Python mà testcontract cần; bổ sung junction
  tới dependency đã cài, focused13PASS và full cuối663PASS. Không đổi assertion.
- Frontend npmrunbuild exit0:Vite+TypeScript đạt, có cảnh báo bundle>500kB giữ nguyên.
  Đây là FE snapshotHEAD với profiletest đã cập nhật, không phải nghiệm thu promptFE
  đang triển khai trong thư mục chính.
- RuffBE scopePASS. Không gọi model/RAGlive/E2Ebrowser để chốtGit. Kết quả live805
  là lịch sử,4completed4failed; không coi là chất lượng đã nghiệm thu toàn tài liệu.
- Artifact/log cục bộ tại tmp/release806, không stage lênGit.

## Dọn dẹp và bảo toàn

Inventory trước worktree:tmp~601MiB chứa report/OCR/runtime; FE.vite~20.5MiB và
dist~3.9MiB đang liên quan FE, giữ lại. Chỉ chọn backendV1/.pytest_cache và
tmp/__pycache__ (~261651byte/12file) sau xác minh paths/nội dung, không link.
Hai lần lệnhxóa bị automaticapprovalreview từ chối với lý do blockedbypolicy;
không chuyển shell/cơ chế khác để vượt chặn. **Cleanup NOT DONE,0file bị xóa.**

MãFE đang làm vẫn nguyên ở mainworktree; không stash/reset/clean, không tự gom vào
commit. Worktree riêng giữ để bổ sung FE sau. Secret/artifact/UTF8/link và staged
diff được kiểm trước commit; không thêm corpus, .env, dependency hoặc rawOCR.

## Git và bàn giao

Nhánh được yêu cầu tên chính xác v1.0.3, không tag release và không merge lênmain.
Push tường minh Gitea trước, chỉ sau thành công mới GitHub; không dùng origin có
nhiều pushURL và không forcepush. Đối chiếu remote tip với local sau push.
Receipt kết quả thực tế ở tmp/release806; final bàn giao nêu hash/remote thực đạt
hoặc lỗi nếu có. Snapshot806 ghi rõ các gate chưa đạt, không gọi checkpoint làGA.

Kết quả thực tế: code checkpoint711b1bc96b401bc8593c12f9210ca3b030d3dc8b
đãpushGitea thành công và ls-remote xác nhận đúng hash. GitHubpush exit1,
GH001/pre-receive hook declined: PDF Cẩm Nang Tuyển Sinh Đại Học Năm2025(1)
162.41MiB đã có trong lịch sử cũ, vượt100MiB. Không phải sourcefile thêm ở806.
Người dùng xác nhận giữ Gitea, để xử lý lịch sử GitHub thành việc riêng; không
rewritehistory, forcepush, LFSmigration hoặc xóaPDF. Commit tài liệu tiếp theo
chỉ bổ sung biên nhận này trên Gitea; GitHub chưa có nhánh v1.0.3.
