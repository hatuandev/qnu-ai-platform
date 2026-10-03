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
    page = doc[-1] # closing page
    pix = page.get_pixmap(dpi=150)
    pil_img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
    w, h = pil_img.size
    arr_gray = np.array(pil_img.convert("L"))
    arr_rgb = np.array(pil_img.convert("RGB"))

    # Red seal detection
    r_chan = arr_rgb[:, :, 0].astype(np.int32)
    g_chan = arr_rgb[:, :, 1].astype(np.int32)
    b_chan = arr_rgb[:, :, 2].astype(np.int32)
    red_mask = (r_chan > 120) & ((r_chan - g_chan) > 35) & ((r_chan - b_chan) > 35)

    red_bottom = red_mask.copy()
    red_bottom[:int(0.40 * h), :] = False
    has_seal = np.count_nonzero(red_bottom) > 400
    seal_y1, seal_y2 = 0, 0
    if has_seal:
        red_rows = np.where(red_bottom.sum(axis=1) > 5)[0]
        seal_y1 = red_rows[0]
        seal_y2 = red_rows[-1]
        print(f"\n=== {pdf_name} ===")
        print(f"Detected red seal from y={seal_y1} ({seal_y1/h*100:.1f}%) to y={seal_y2} ({seal_y2/h*100:.1f}%)")
    else:
        print(f"\n=== {pdf_name} ===")
        print("No red seal detected")
