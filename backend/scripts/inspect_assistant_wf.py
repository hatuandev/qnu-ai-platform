import asyncio
import json
from app.core.database import AsyncSessionFactory
from app.modules.assistants.service import assistant_service
from app.modules.workflows.service import workflow_service

async def main():
    async with AsyncSessionFactory() as db:
        ast = await assistant_service.get_assistant(db, 'ast_admissions')
        print(f"Assistant: code={ast.code}, wf_id={ast.workflow_id}, col_id={ast.collection_id}")
        if ast.workflow_id:
            wf = await workflow_service.get_workflow(db, ast.workflow_id)
            print(f"Workflow nodes: {len(wf.definition.get('nodes', []))}")
            for n in wf.definition.get('nodes', []):
                print(f"  Node {n.get('id')}: type={n.get('type')}, config={json.dumps(n.get('data', {}).get('config', {}), ensure_ascii=False)}")

if __name__ == '__main__':
    asyncio.run(main())
