# Phiên 790 — RAG có ngữ cảnh và phạm vi từ nguồn

Ngày: 2026-11-01. Yêu cầu: triển khai lần lượt các đề xuất sau khi tham khảo ảnh: metadata có bằng chứng, xác định phạm vi, contextual search, glossary và kiểm chứng ngoài bộ tuyển sinh. Giữ thay đổi cũ của người dùng.

## Triển khai

1. Siết `knowledge/metadata.py`: proof phải thuộc target; quote bảng còn phải xuất hiện trong ô/hàng được chọn **và** text canonical, không chấp nhận câu nối ô do code tự dựng. Năm/ngành/khóa vẫn ở target cục bộ; unknown không được suy từ tên file. Không thay quy trình duyệt metadata/hash.
2. `index/query_scope.py`: catalog lấy từ generation hiện hành, sau kiểm quyền và binding publication, xác minh manifest. Ghép nhãn có nguồn, giữ vai trò năm; đếm 4 chữ số không mặc nhiên là năm. Nhãn dài thắng nhãn ngắn cùng vị trí. Giữ filter cố định, OR của các bộ AND; mơ hồ hỏi lại bằng 409, không tự tạo cặp ngành/năm hoặc mở filter khi no_match. Context hàng xóm/dependency nhận cùng các scope. Đây là planner bảo thủ, chưa hiểu mọi cách diễn đạt/mã mới.
3. `index/contextual.py`: recipe opt-in `qnu.search-context/v1`, lưu body gốc/hash và prefix riêng trong structure đã seal; search text dùng embedding + PostgreSQL FTS + rerank. Answer projection bỏ phần search_context, tiếp tục đọc canonical đã ghim. Cap byte thực và nguồn bảng giữ nguyên. Request idempotency cũ vẫn replay được khi option tắt. Không migration.
4. Glossary từ các cặp tên đầy đủ/viết tắt có initials khớp trong block canonical đã được cite. Có quote/citation, version/publication qua binding manifest, không từ điển trường/ngành. Mở rộng query có scope, giữ câu gốc; nhiều nghĩa hỏi lại, nguồn rút xuất bản không góp glossary.
5. Thêm test generic với ngành/đợt/năm tổng hợp khác bộ admissions, negative scope/provenance/budget/tampering/auth/withdrawal. Không sửa gold 53 câu.

Frontend: lựa chọn tạo index có ngữ cảnh, tìm thử catalog scope và policy trợ lý; giữ default explicit/recipe cũ. Map form/request không làm mất option; summary cho biết lựa chọn. Prompt answer **v14** thêm cách đọc `metadata_filter.any_of`. Các hội thoại cũ vẫn giữ policy snapshot, còn prompt code mới có version mới để đánh giá riêng.

Phạm vi file: metadata, index contextual/query_scope/schemas/service/execution/search/scope/presentation; RAG policy/service/context/table_support/projection/drafting/schemas; fixture và regression mới 790; frontend types/form/schema/index transport/query/UI/assistant/summary và test contract/UI. Thay đổi cũ các phiên 777–789 được giữ.

## Bằng chứng kiểm tra

| Kiểm tra | Kết quả |
|---|---|
| Tái hiện validator cũ từ HEAD trong module riêng | RED: nhận proof ở block khác cùng OCR run; bản hiện tại chặn `retrieval_metadata_invalid` |
| Unit trọng tâm | Lần đầu 63 PASS / 1 FAIL do case đã nêu intake rõ, không phải ca thiếu intake; chỉnh đúng dữ liệu ca kiểm thử rồi 64 PASS |
| Unit generic cuối | 15 PASS, gồm thêm quote canonical không được tự nối ô |
| Full unit cuối | **645 PASS / 1 FAIL**, exit 1; exact lỗi nền `test_source_purge_716.py::test_accept_rechecks_publication_after_preview_before_preparing_purge` / invalid_identity |
| API broad cô lập | 68 PASS / 1 FAIL, 571.68s; lỗi fixture che biến request khiến chưa bật contextual recipe; không gọi kết quả này PASS |
| API sau sửa fixture | 4 PASS / 3 ERROR, 51.65s; phát hiện reserve cố định 2048 khiến bảng không vừa default 3000 byte |
| API cuối sau sửa reserve | **7 PASS**, 55.70s, exit 0; new recipe/catalog/glossary/withdrawal/auth/tamper và table prompt v14/context/scope trước TopK |
| Frontend targeted cuối | **30 PASS**, exit 0; form roundtrip, request opt-in và checkbox giữ năm |
| Frontend full | **594 PASS / 33 FAIL**, exit 1; so exact IDs với log789: 33 cũ, 0 mới, 0 mất |
| Build / E2E TypeScript / Biome / Ruff / diff whitespace | PASS; build có cảnh báo bundle size cũ |

Full unit lần đầu lỗi môi trường tmp_path (`WinError 5`, 24 ERROR) ngoài lỗi purge; chạy với basetemp riêng giải quyết setup. Unit có thêm sửa đổi thì chạy lại final gate, không bỏ assertion. Một lượt FE ban đầu lỗi matcher mới `toBeChecked` không được đăng ký; đổi sang kiểm aria-checked thật. Lỗi `rag-ui-674` thiếu auth provider là exact baseline và vẫn FAIL trong full suite.

Lệnh chính từ `backendV1`: `.venv/Scripts/python.exe -m pytest tests/unit -q --basetemp ../tmp/pytest790-unit-complete`; Ruff scoped trên file sửa. API dùng helper cục bộ `tmp/run-rag790-final2.py`: tạo DB `qnu_v1_test_*`, migrate, pytest 7 case, drop DB trong finally, namespace/storage test riêng. PostgreSQL/Qdrant thật, các model là loopback giả. Frontend: Vitest 2 file trọng tâm/full `--reporter=dot`, `npm run build`, `npm run test:e2e:typecheck`, Biome scoped.

Log: `tmp/verification790-integration.log`, `tmp/verification790_final-integration.log`, `tmp/verification790_final2-integration.log`, `tmp/verification790-unit-complete.log`, `tmp/verification790-fe-final.log`, `tmp/verification790-fe-full.log`, `tmp/verification790-build.log`, `tmp/verification790-e2e-typecheck.log`. Artifact chức năng: `backendV1/storage/context790/functional-comparison.json`, cùng generation, dense/hybrid, `quality_claim:false`. Test mô hình giả không chứng minh chất lượng semantic/model thật tăng.

## Giới hạn và bàn giao

- **NOT RUN** model thật/53 câu/reindex 3 PDF/restart/change assistant live. Phiên hiện hữu 93faa11f0caf và cohort789 giữ nguyên; I25-04 uncertain cũ không được gửi lại.
- UI đã kiểm bằng test tương tác và build, chưa đối chiếu ảnh desktop/mobile trong phiên này.
- Chưa triển khai late chunking. Cần adapter token embedding/offset và benchmark riêng, không đồng nhất nó với thêm prefix.
- Metadata cần review nguồn trước bật catalog; không tự gán năm chung cả file. Glossary bảo thủ, giới hạn 32 định nghĩa, chưa bao phủ mọi kiểu viết tắt. Clarification hiện là thông báo 409, chưa có UI hội thoại chọn facet riêng.
- Đã thêm [hướng dẫn vận hành](../quy_trinh/V1_RAG_NGU_CANH_VA_PHAM_VI.md). Tạo generation mới có chủ đích sẽ thay generation active theo quy trình cũ, không mặc nhiên là shadow index.
- Nghiệm thu chất lượng bước sau: corpus/gold độc lập, snapshot/revision/config/prompt/recipe cố định, mỗi câu một lượt, báo cả lỗi và uncertain. Không gộp cohort hoặc retry chọn đáp án xanh.
