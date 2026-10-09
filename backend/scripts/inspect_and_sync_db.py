import asyncio
import sys
from pathlib import Path

# Ensure backend root is in sys.path
backend_root = Path(__file__).resolve().parent.parent
if str(backend_root) not in sys.path:
    sys.path.insert(0, str(backend_root))

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

from sqlalchemy import select

from app.core.database import AsyncSessionFactory
from app.modules.assistants.models import AssistantModel
from app.modules.assistants.seeder import seed_standard_assistants
from app.modules.modelops.models import ModelProviderConfig
from app.modules.modelops.schemas import SystemModelDefaultsUpdate
from app.modules.modelops.services.model_catalog_service import (
    DEFAULT_QNU_OCR_COMBO_CHAIN,
    model_catalog_service,
)
from app.modules.modelops.services.provider_service import provider_service


async def main():
    async with AsyncSessionFactory() as db:
        print("--- [1] Checking Current Providers in DB ---")
        res = await db.execute(select(ModelProviderConfig))
        providers = res.scalars().all()
        for p in providers:
            print(f"- {p.id}: {p.name} ({p.provider_type}) | Model: {p.model_name}")

        print("\n--- [2] Checking Current Assistants in DB ---")
        res = await db.execute(select(AssistantModel))
        assistants = res.scalars().all()
        for a in assistants:
            cfg = a.config or {}
            mp = cfg.get("model_policy", {})
            print(f"- {a.code}: {a.name} -> primary_model: {mp.get('primary_model')} | provider: {mp.get('preferred_provider_id')}")

        print("\n--- [3] Checking System Defaults ---")
        sys_defaults = await model_catalog_service.get_system_model_defaults(db)
        print(f"Current OCR Chain (len={len(sys_defaults.defaults.ocr_combo_chain)}):")
        for idx, item in enumerate(sys_defaults.defaults.ocr_combo_chain, 1):
            print(f"  * P{idx}: {item.provider_id} - {item.model_name} (active={item.is_active})")

        print("\n=== RUNNING SEEDS & SYNC ===")
        # 1. Seed providers (overwrite=True to update any modified provider specs like RTX 5090)
        seeded_provs = await provider_service.seed_default_providers(db, overwrite=True)
        print(f"Seeded {len(seeded_provs)} providers successfully.")

        # 2. Update system defaults OCR chain to use the latest DEFAULT_QNU_OCR_COMBO_CHAIN
        from app.modules.modelops.services.model_catalog_service import DEFAULT_INITIAL_COMBOS
        update_req = SystemModelDefaultsUpdate(
            ocr_combo_chain=DEFAULT_QNU_OCR_COMBO_CHAIN,
            default_ocr_provider_id="prov_gemini",
            default_ocr_model="gemini-3.1-flash-lite",
            default_embedding_provider_id="prov_rtx5090_vllm",
            default_embedding_model="bge-m3",
            default_reranker_provider_id="prov_rtx5090_vllm",
            default_reranker_model="bge-reranker-v2-m3",
            model_combos=DEFAULT_INITIAL_COMBOS,
        )
        updated_defaults = await model_catalog_service.update_system_model_defaults(db, update_req)
        print(f"Updated system defaults OCR chain (len={len(updated_defaults.defaults.ocr_combo_chain)}).")
        print(f"Updated model_combos in system defaults (len={len(updated_defaults.defaults.model_combos)}).")

        # 3. Seed assistants
        seeded_ast_count = await seed_standard_assistants(db)
        print(f"Seed assistants completed. Count added/checked: {seeded_ast_count}")

        # 4. Verify after sync
        print("\n=== VERIFYING AFTER SYNC ===")
        res = await db.execute(select(ModelProviderConfig).where(ModelProviderConfig.id == "prov_rtx5090_vllm"))
        rtx_prov = res.scalar_one_or_none()
        if rtx_prov:
            print(f"[OK] prov_rtx5090_vllm found in DB! Name: {rtx_prov.name}, URL: {rtx_prov.api_base_url}, Model: {rtx_prov.model_name}")
            extra = rtx_prov.extra_config or {}
            print(f"     Models: {extra.get('models')}")
        else:
            print("[FAIL] prov_rtx5090_vllm NOT found in DB!")

        res = await db.execute(select(AssistantModel).where(AssistantModel.code.in_(["drafting", "question_bank", "regulations", "admissions", "library"])))
        for a in res.scalars().all():
            cfg = a.config or {}
            mp = cfg.get("model_policy", {})
            print(f"[OK] Assistant {a.code}: primary_model={mp.get('primary_model')}, provider={mp.get('preferred_provider_id')}")

        sys_defaults = await model_catalog_service.get_system_model_defaults(db)
        print("[OK] System Defaults OCR Chain (top 2):")
        for idx, item in enumerate(sys_defaults.defaults.ocr_combo_chain[:2], 1):
            print(f"  * P{idx}: {item.provider_id} - {item.model_name} (active={item.is_active})")

if __name__ == "__main__":
    asyncio.run(main())
