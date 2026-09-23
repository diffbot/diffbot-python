import httpx
import pytest

from diffbot import Diffbot, DiffbotAsync


"""
Endpoint configuration
"""


def test_dql_defaults_to_public_endpoint():
    def handler(request: httpx.Request) -> httpx.Response:
        assert str(request.url).startswith("https://kg.diffbot.com/kg/v3/dql")
        return httpx.Response(200, json={"data": []})

    db = Diffbot(token="test-token", transport=httpx.MockTransport(handler))
    db.dql("type:Organization")


def test_dql_honors_custom_dql_url():
    def handler(request: httpx.Request) -> httpx.Response:
        assert str(request.url).startswith("http://localhost:8080/kg/v3/dql")
        return httpx.Response(200, json={"data": []})

    db = Diffbot(
        token="test-token",
        dql_url="http://localhost:8080/kg/v3/dql",
        transport=httpx.MockTransport(handler),
    )
    db.dql("type:Organization")


def test_dql_parallel_honors_custom_dql_url():
    def handler(request: httpx.Request) -> httpx.Response:
        assert str(request.url).startswith("http://localhost:8080/kg/v3/dql")
        return httpx.Response(200, json={"hits": 1})

    db = Diffbot(
        token="test-token",
        dql_url="http://localhost:8080/kg/v3/dql",
        transport=httpx.MockTransport(handler),
    )
    results = db.dql_parallel([{"query": "type:Organization", "size": 0}] * 2)
    assert results == [{"hits": 1}, {"hits": 1}]


def test_ontology_honors_custom_ontology_url():
    def handler(request: httpx.Request) -> httpx.Response:
        assert str(request.url) == "http://localhost:8080/kg/ontology"
        return httpx.Response(200, json={"types": {"Organization": {"fields": {}}}})

    db = Diffbot(
        token="test-token",
        ontology_url="http://localhost:8080/kg/ontology",
        transport=httpx.MockTransport(handler),
    )
    assert db.dql_fetch_ontology().types() == ["Organization"]


@pytest.mark.anyio
async def test_async_dql_honors_custom_dql_url():
    def handler(request: httpx.Request) -> httpx.Response:
        assert str(request.url).startswith("http://localhost:8080/kg/v3/dql")
        return httpx.Response(200, json={"data": []})

    db = DiffbotAsync(
        token="test-token",
        dql_url="http://localhost:8080/kg/v3/dql",
        transport=httpx.MockTransport(handler),
    )
    await db.dql("type:Organization")


@pytest.mark.anyio
async def test_async_ontology_honors_custom_ontology_url():
    def handler(request: httpx.Request) -> httpx.Response:
        assert str(request.url) == "http://localhost:8080/kg/ontology"
        return httpx.Response(200, json={"types": {"Person": {"fields": {}}}})

    db = DiffbotAsync(
        token="test-token",
        ontology_url="http://localhost:8080/kg/ontology",
        transport=httpx.MockTransport(handler),
    )
    ont = await db.dql_fetch_ontology()
    assert ont.types() == ["Person"]


"""
Live
"""

@pytest.mark.live
def test_live_dql(db):
    result = db.dql('type:Organization name:"Diffbot"', size=1)
    assert "data" in result
    assert len(result["data"]) > 0
    entity = result["data"][0]["entity"]
    assert entity.get("name") == "Diffbot"
