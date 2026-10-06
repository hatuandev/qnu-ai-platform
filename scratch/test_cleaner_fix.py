import os
import sys
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
import re

sys.path.insert(0, os.path.abspath("backend"))

# Sample raw table markdown before cleaner collapsed it
sample_table = """| STT | Tên ngành | Khối ngành | Thời gian học (năm) | Hình thức đào tạo | Học phí toàn khóa | Ghi chú |
| :---: | :--- | :--- | :--- | :--- | :--- | :--- |
| 1 | Kế toán | III | 2 | Tốt nghiệp trình độ cao đẳng cùng nhóm ngành | 23.660.000 | |
| | | | | Học phí đợt 1 | 5.600.000 | Học phí thu theo 4 đợt |
| | | | | Học phí đợt 2 | 5.600.000 | |
| | | | | Học phí đợt 3 | 6.230.000 | |
| | | | | Học phí đợt 4 | 6.230.000 | |
| | | | 2,5 | Văn bằng đại học 2 | 30.550.000 | |
| | | | | Học phí đợt 1 | 5.600.000 | Học phí thu theo 5 đợt |
| | | | | Học phí đợt 2 | 5.600.000 | |
| | | | | Học phí đợt 3 | 6.230.000 | |
| | | | | Học phí đợt 4 | 6.230.000 | |
| | | | | Học phí đợt 5 | 6.890.000 | |"""

from app.modules.ocr.cleaner import merge_ocr_orphan_table_rows

print("=== CURRENT merge_ocr_orphan_table_rows ===")
print(merge_ocr_orphan_table_rows(sample_table))
