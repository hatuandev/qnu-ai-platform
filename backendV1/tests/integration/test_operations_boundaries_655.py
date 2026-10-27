"""Operations and retrieval boundaries must exist before they can be wired into UI."""

import pytest

from qnu.domains.knowledge.index.schemas import SearchRequest
from tests.integration.compiler_support import processed_input
from tests.integration.knowledge_support import API, PLATFORM, as_actor


@pytest.mark.parametrize("kind", ["jobs", "backups", "retention"])
def test_operations_boundary(client, kind):
    data = processed_input(client, code="operations-boundary")
    as_actor(PLATFORM)
    result = client.get(f"{API}/workspaces/{data['workspace']['id']}/operations/{kind}")
    assert result.status_code == 200, result.text


def test_hybrid_request_boundary():
    req = SearchRequest(query="Tìm nguồn", mode="hybrid", candidate_k=20)
    assert req.mode == "hybrid"
