import sys
import numpy as np
from PIL import Image
import pymupdf as fitz

sys.stdout.reconfigure(encoding='utf-8')

for pdf_name in [
    "TB2302_Thong_bao_tuyen_sinh_dao_tao_tu_xa_trinh_do_dai_hoc.pdf",
    "TB2618_Tuyen_sinh_dai_hoc_vua_lam_vua_hoc_GDTX_Gia_Lai.pdf"
]:
    pdf_path = f"docs/tai_lieu/tuyen_sinh/vua_lam_vua_hoc/{pdf_name}"
    doc = fitz.open(pdf_path)
    page = doc[0]
    pix = page.get_pixmap(dpi=150)
    pil_img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
    w, h = pil_img.size
    arr_gray = np.array(pil_img.convert("L"))

    bg_level = float(np.percentile(arr_gray, 90))
    ink_thresh = min(190, int(bg_level * 0.78))
    cleaned = (arr_gray < ink_thresh).astype(np.int32)

    # Vertical line bridging (bridge gaps up to 6px vertically)
    bridged_v = cleaned.copy()
    for s in [1, 2, 3, 4, 5, 6]:
        bridged_v[:-s, :] |= cleaned[s:, :]
        bridged_v[s:, :] |= cleaned[:-s, :]

    # Detect vertical lines with continuous run >= 150px
    min_v_len = max(100, int(h * 0.08))
    col_v_lines = []
    for x in range(int(0.05 * w), int(0.95 * w)):
        col = bridged_v[:, x]
        diffs = np.diff(np.pad(col, (1, 1), "constant"))
        starts = np.where(diffs == 1)[0]
        ends = np.where(diffs == -1)[0]
        if len(starts) > 0 and len(ends) > 0:
            lens = ends - starts
            for st, en, l in zip(starts, ends, lens):
                if l >= min_v_len:
                    col_v_lines.append((x, st, en, l))

    print(f"\n=== {pdf_name} ===")
    print(f"Total strong vertical line segments (len >= {min_v_len}px): {len(col_v_lines)}")
    # Find overlapping vertical ranges that have >= 3 columns
    # Group vertical segments that span similar y ranges
    if col_v_lines:
        y_spans = [(st, en) for x, st, en, l in col_v_lines]
        min_y = min(st for st, en in y_spans)
        max_y = max(en for st, en in y_spans)
        xs = sorted(list(set(x for x, st, en, l in col_v_lines)))
        print(f"Vertical lines span: y = {min_y} ({min_y/h*100:.1f}%) to {max_y} ({max_y/h*100:.1f}%), {len(xs)} x-positions from {xs[0]} ({xs[0]/w*100:.1f}%) to {xs[-1]} ({xs[-1]/w*100:.1f}%)")
