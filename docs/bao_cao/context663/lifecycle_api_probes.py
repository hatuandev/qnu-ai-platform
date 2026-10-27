"""Independent API probes: pausing/archiving must fence an already running turn."""
import asyncio
import pytest
from tests.integration.knowledge_support import API, EDITOR, PLATFORM, as_actor
from tests.integration.test_answers_api_648 import ready
from tests.integration.test_index_api_647 import indexed
from tests.integration.test_conversations_649 import chat_session, send

@pytest.mark.parametrize("route", ["assistant_put", "conversation_put"])
def test_existing_update_routes_fence_turn_after_stop_and_resume(client, chat_session, monkeypatch, route):
    from qnu.main import app
    from qnu.domains.assistants.schemas import AssistantConfig
    data = chat_session
    original = app.state.container.chat_model
    class StopAndResumeDuringChat:
        async def complete(self, messages, request):
            result = await original.complete(messages, request)
            def change():
                if route == "assistant_put":
                    as_actor(PLATFORM)
                    url = f"{API}/workspaces/{data['workspace']['id']}/assistants/{data['assistant']['id']}"
                    config = AssistantConfig.model_validate({key: data['assistant'][key] for key in AssistantConfig.model_fields}).model_dump()
                    for active in (False, True):
                        response = client.put(url, json={**config, "is_active": active, "expected_revision": data['assistant']['revision']})
                        assert response.status_code == 200, response.text
                else:
                    for status in ("archived", "active"):
                        response = client.put(data['conversation_url'], json={"title": "Synthetic review", "status": status})
                        assert response.status_code == 200, response.text
                as_actor(EDITOR)
            await asyncio.to_thread(change)
            return result
    monkeypatch.setattr(app.state.container, 'chat_model', StopAndResumeDuringChat())
    response = send(client, data)
    as_actor(EDITOR)
    turn = client.get(data['conversation_url']+'/turns').json()[0]
    observed = {"http_status": response.status_code, "turn_status": turn['status'], "has_result": turn['result'] is not None}
    assert observed == {"http_status": 409, "turn_status": "cancelled", "has_result": False}, observed
