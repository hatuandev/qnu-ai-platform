import asyncio
import json
from app.core.database import AsyncSessionFactory
from app.modules.workflows.service import workflow_service

async def main():
    async with AsyncSessionFactory() as db:
        spec = await workflow_service.get_workflow_spec(db, "admissions-assistant")
        with open("workflow_admissions_spec.json", "w", encoding="utf-8") as f:
            f.write(json.dumps(spec.model_dump(mode="json"), indent=2, ensure_ascii=False))
        print("Spec written to workflow_admissions_spec.json successfully!")

if __name__ == '__main__':
    asyncio.run(main())
