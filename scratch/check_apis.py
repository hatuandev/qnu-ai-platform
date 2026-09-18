import urllib.request
import json
import sys

sys.stdout.reconfigure(encoding="utf-8")

print("=== 1. DOCUMENT TYPES API ===")
r1 = json.loads(urllib.request.urlopen("http://127.0.0.1:8001/platform/v1alpha1/document-types", timeout=5).read().decode("utf-8"))
print(f"Tổng số loại văn bản: {len(r1)}")
categories = {}
nd30_count = 0
for d in r1:
    cat = d.get("category_name", "Khác")
    categories[cat] = categories.get(cat, 0) + 1
    if d.get("nd30"):
        nd30_count += 1

print(f"Số loại văn bản chuẩn NĐ 30: {nd30_count}")
print("Phân bố theo nhóm:")
for cat, count in categories.items():
    print(f" - {cat}: {count} loại")

print("\n=== 2. NODE CATALOG API ===")
r2 = json.loads(urllib.request.urlopen("http://127.0.0.1:8001/platform/v1alpha1/nodes", timeout=5).read().decode("utf-8"))
items = r2.get("items", [])
print(f"Tổng số Node Manifests: {len(items)}")
node_cats = {}
for n in items:
    cat = n.get("category", "other")
    node_cats[cat] = node_cats.get(cat, 0) + 1
    print(f" - [{cat.upper()}] {n.get('type')}: {n.get('display_name')} (v{n.get('version')})")

print(f"Phân bố node categories: {node_cats}")
