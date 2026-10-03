import httpx
import json

resp = httpx.get("http://localhost:3000/api/v1/modelops/defaults", timeout=5.0)
print("Status:", resp.status_code)
if resp.status_code == 200:
    data = resp.json()
    defaults = data.get("defaults", {})
    print("default_ocr_mode:", defaults.get("default_ocr_mode"))
    print("default_ocr_combo_id:", defaults.get("default_ocr_combo_id"))
    print("default_ocr_model:", defaults.get("default_ocr_model"))
    print("\nocr_combo_chain:")
    print(json.dumps(defaults.get("ocr_combo_chain"), indent=2, ensure_ascii=False))
    print(f"\nmodel_combos count: {len(defaults.get('model_combos') or [])}")
    for c in defaults.get("model_combos") or []:
        print(f"\nCombo: {c.get('id')} - {c.get('name')} (Task: {c.get('task_type')}, Default: {c.get('is_default')})")
        for m in c.get("models") or []:
            print(f"   Step: {m.get('model_name')} [{m.get('provider_name')}] (provider_id: {m.get('provider_id')})")
else:
    print(resp.text)
