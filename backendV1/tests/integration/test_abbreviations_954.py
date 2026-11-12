"""A1: the index manifest persists the mined abbreviation catalog for query expansion."""

from qnu.domains.knowledge.index import abbreviations
from tests.integration.index_support import execute_index
from tests.integration.test_index_api_647 import indexed  # noqa: F401


def test_index_manifest_carries_the_abbreviation_catalog(client, indexed):  # noqa: F811
    data = indexed
    run = data["index_run"]["id"]
    assert execute_index(client, run) == "completed"
    response = client.get(f"{data['base']}/indexing-runs/{run}/manifest")
    assert response.status_code == 200, response.text
    catalog = response.json()["config"]["abbreviations"]
    assert catalog["version"] == abbreviations.VERSION
    assert isinstance(catalog["definitions"], list)
    assert catalog["truncated"] is False
    assert all(
        {"alias", "expansion", "citation", "quote"} <= set(entry)
        for entry in catalog["definitions"]
    )
