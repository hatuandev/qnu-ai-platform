import asyncio
import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from sqlalchemy import select

from app.core.database import AsyncSessionFactory
from app.modules.assistants.models import AssistantModel
from app.modules.assistants.seeder import STANDARD_ASSISTANTS


async def sync_prompts():
    async with AsyncSessionFactory() as db:
        for ast_data in STANDARD_ASSISTANTS:
            res = await db.execute(
                select(AssistantModel).where(AssistantModel.id == ast_data["id"])
            )
            ast = res.scalars().first()
            if ast:
                ast.system_prompt = ast_data["system_prompt"]
                print(f"Updated assistant '{ast.id}' ({ast.name}) with new system prompt.")
        await db.commit()
        print("All standard assistant prompts synced successfully.")


if __name__ == "__main__":
    asyncio.run(sync_prompts())
