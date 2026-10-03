import asyncio
import json
from sqlalchemy import select
from app.core.database import AsyncSessionFactory
from app.modules.modelops.models import ModelProviderConfig

async def main():
    async with AsyncSessionFactory() as db:
        stmt = select(ModelProviderConfig).where(ModelProviderConfig.id == "system_model_defaults")
        res = await db.execute(stmt)
        cfg_record = res.scalar_one_or_none()
        if not cfg_record:
            print("No system_model_defaults record found!")
            return
        defaults = (cfg_record.extra_config or {}).get("defaults") or {}
        print("default_ocr_mode:", defaults.get("default_ocr_mode"))
        print("default_ocr_combo_id:", defaults.get("default_ocr_combo_id"))
        print("default_ocr_model:", defaults.get("default_ocr_model"))
        print("\n=== OCR COMBO CHAIN ===")
        print(json.dumps(defaults.get("ocr_combo_chain"), indent=2, ensure_ascii=False))

        combos = defaults.get("model_combos") or []
        print(f"\n=== MODEL COMBOS ({len(combos)}) ===")
        for c in combos:
            print(f"\nCombo ID: {c.get('id')} | Name: {c.get('name')} | Task: {c.get('task_type')} | Default: {c.get('is_default')}")
            for idx, m in enumerate(c.get("models") or []):
                print(f"  Step {idx+1}: {m.get('model_name')} (Provider: {m.get('provider_name')}, ProviderID: {m.get('provider_id')})")

asyncio.run(main())
