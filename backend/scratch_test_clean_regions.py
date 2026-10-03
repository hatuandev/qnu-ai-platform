def cleanStudioRegions(regions):
    tables = [r for r in regions if r["type"] == "table"]
    nonTables = [r for r in regions if r["type"] != "table"]

    print(f"Initial: {len(tables)} tables, {len(nonTables)} non-tables")

    validTables = []
    for i, ti in enumerate(tables):
        areaI = ti["width"] * ti["height"]
        if areaI <= 0:
            continue
        keep = True
        for j, tj in enumerate(tables):
            if i == j:
                continue
            areaJ = tj["width"] * tj["height"]
            if areaJ > areaI:
                ix0 = max(ti["left"], tj["left"])
                iy0 = max(ti["top"], tj["top"])
                ix1 = min(ti["left"] + ti["width"], tj["left"] + tj["width"])
                iy1 = min(ti["top"] + ti["height"], tj["top"] + tj["height"])
                if ix1 > ix0 and iy1 > iy0:
                    interArea = (ix1 - ix0) * (iy1 - iy0)
                    if interArea / areaI >= 0.7:
                        keep = False
                        break
        if keep:
            validTables.append(ti)

    print(f"Valid tables: {len(validTables)}")

    validNonTables = []
    for r in nonTables:
        if r["type"] in ("signature", "header"):
            validNonTables.append(r)
            continue
        areaR = r["width"] * r["height"]
        if areaR <= 0:
            validNonTables.append(r)
            continue

        totalInterArea = 0
        cx = r["left"] + r["width"] / 2.0
        cy = r["top"] + r["height"] / 2.0

        discard = False
        for t in validTables:
            if (
                cx >= t["left"] - 0.5
                and cx <= t["left"] + t["width"] + 0.5
                and cy >= t["top"] - 0.5
                and cy <= t["top"] + t["height"] + 0.5
            ):
                print(f"Discarding {r['label']} ({r['type']}) because center ({cx}, {cy}) is inside table ({t['left']}, {t['top']}, {t['width']}, {t['height']})")
                discard = True
                break

            ix0 = max(r["left"], t["left"])
            iy0 = max(r["top"], t["top"])
            ix1 = min(r["left"] + r["width"], t["left"] + t["width"])
            iy1 = min(r["top"] + r["height"], t["top"] + t["height"])
            if ix1 > ix0 and iy1 > iy0:
                totalInterArea += (ix1 - ix0) * (iy1 - iy0)

        if discard:
            continue

        if totalInterArea / areaR >= 0.4:
            print(f"Discarding {r['label']} ({r['type']}) because overlap ratio {totalInterArea/areaR:.2f} >= 0.4")
            continue

        validNonTables.append(r)

    print(f"Valid non-tables: {len(validNonTables)}")
    return validTables + validNonTables

boxes = [
    {"type": "header", "label": "Phần đầu văn bản", "left": 10.0, "top": 4.0, "width": 79.0, "height": 8.0},
    {"type": "title", "label": "Tiêu đề", "left": 15.0, "top": 15.0, "width": 70.0, "height": 6.0},
    {"type": "text", "label": "Khối văn bản", "left": 10.0, "top": 23.0, "width": 79.0, "height": 4.0},
    {"type": "table", "label": "Bảng dữ liệu", "left": 20.0, "top": 31.0, "width": 60.0, "height": 10.0},
    {"type": "list", "label": "Danh sách", "left": 10.0, "top": 43.0, "width": 79.0, "height": 32.0},
]

res = cleanStudioRegions(boxes)
print(f"Final kept regions: {len(res)}")
for r in res:
    print(" ", r["type"], r["label"], r["top"], r["left"], r["width"], r["height"])
