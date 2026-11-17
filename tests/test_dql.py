import json

import httpx
import pytest

from diffbot import APIError, Diffbot, DiffbotAsync, NotFoundError, ValidationError


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
Errors
"""


def test_dql_404_raises_not_found_error():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(404, json={"message": "no such report"})

    db = Diffbot(token="test-token", transport=httpx.MockTransport(handler))
    with pytest.raises(NotFoundError) as exc_info:
        db.dql("type:Organization")
    assert isinstance(exc_info.value, APIError)
    assert exc_info.value.message == "no such report"


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


"""
DQL is sent as POST with a JSON body
"""


def _capture():
    seen = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return httpx.Response(200, json={"data": [], "hits": 0})

    return seen, handler


def test_dql_posts_json_body_with_token_in_query():
    seen, handler = _capture()
    db = Diffbot(token="secret-tok", transport=httpx.MockTransport(handler))
    db.dql('type:Organization name:"Diffbot"')
    (req,) = seen
    assert req.method == "POST"
    assert req.headers["content-type"] == "application/json"
    assert req.url.params["token"] == "secret-tok"
    assert "query" not in req.url.params
    assert "Diffbot" not in str(req.url)
    body = json.loads(req.content)
    assert body == {"query": 'type:Organization name:"Diffbot"', "size": 10}
    assert "token" not in body


def test_dql_body_defaults_and_options():
    seen, handler = _capture()
    db = Diffbot(token="t", transport=httpx.MockTransport(handler))
    db.dql("q", size=0, from_=5, format="csv", filter="f", exportspec="a;b", extra={"jsonmode": "extended", "n": 3})
    body = json.loads(seen[0].content)
    assert body == {
        "query": "q", "size": 0, "from": 5, "format": "csv", "filter": "f",
        "exportspec": "a;b", "jsonmode": "extended", "n": 3,
    }
    seen.clear()
    db.dql("q", format="json", from_=0)
    assert json.loads(seen[0].content) == {"query": "q", "size": 10}


def test_dql_long_query_is_not_in_url():
    seen, handler = _capture()
    db = Diffbot(token="t", transport=httpx.MockTransport(handler))
    query = " OR ".join(f'name:"Company {i}"' for i in range(1000))
    assert len(query) > 8000
    db.dql(query, size=0)
    assert len(str(seen[0].url)) < 200
    assert json.loads(seen[0].content)["query"] == query


def test_dql_retries_post_on_503():
    calls = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(request.method)
        if len(calls) == 1:
            return httpx.Response(503, text="busy")
        return httpx.Response(200, json={"hits": 1})

    from diffbot import RetryPolicy

    db = Diffbot(token="t", transport=httpx.MockTransport(handler), retry=RetryPolicy(base_delay=0, jitter=False))
    assert db.dql("q", size=0) == {"hits": 1}
    assert calls == ["POST", "POST"]


def test_dql_get_escape_hatch_still_works():
    seen, handler = _capture()
    db = Diffbot(token="t", transport=httpx.MockTransport(handler))
    db.request("GET", db.dql_url, params={"token": "t", "query": "q", "size": 1})
    assert seen[0].method == "GET"
    assert seen[0].url.params["query"] == "q"


@pytest.mark.anyio
async def test_async_dql_posts_json_body_with_token_in_query():
    seen, handler = _capture()
    db = DiffbotAsync(token="secret-tok", transport=httpx.MockTransport(handler))
    await db.dql("type:Person", size=0, from_=2)
    (req,) = seen
    assert req.method == "POST"
    assert req.url.params["token"] == "secret-tok"
    assert "query" not in req.url.params
    assert json.loads(req.content) == {"query": "type:Person", "size": 0, "from": 2}


@pytest.mark.anyio
async def test_async_dql_parallel_posts():
    seen, handler = _capture()
    db = DiffbotAsync(token="t", transport=httpx.MockTransport(handler))
    await db.dql_parallel([{"query": "a", "size": 0}, {"query": "b", "size": 0}])
    assert {r.method for r in seen} == {"POST"}
    assert sorted(json.loads(r.content)["query"] for r in seen) == ["a", "b"]


"""
Return decoding per format (csv/jsonl used to crash in response.json())
"""

JSONL = b'{"score": 1, "entity": {"name": "A"}}\n\n{"score": 2, "entity": {"name": "B"}}\n'


def _mk(content, **kw):
    return Diffbot(token="t", transport=httpx.MockTransport(lambda r: httpx.Response(200, content=content, **kw)))


def test_dql_csv_returns_text():
    assert _mk(b"Name\nDiffbot\n").dql("q", format="csv") == "Name\nDiffbot\n"


def test_dql_csv_raw_returns_bytes():
    assert _mk(b"Name\nDiffbot\n").dql("q", format="csv", raw=True) == b"Name\nDiffbot\n"


@pytest.mark.parametrize("fmt", ["xls", "xlsx"])
def test_dql_excel_returns_bytes(fmt):
    payload = bytes(range(256))
    assert _mk(payload).dql("q", format=fmt) == payload


def test_dql_jsonl_returns_entity_iterator():
    result = _mk(JSONL).dql("q", format="jsonl")
    assert not isinstance(result, (list, dict, bytes, str))
    assert [e["score"] for e in result] == [1, 2]


def test_dql_jsonl_raw_returns_bytes():
    assert _mk(JSONL).dql("q", format="jsonl", raw=True) == JSONL


def test_dql_json_raw_returns_bytes():
    assert _mk(b'{"hits": 1}').dql("q", raw=True) == b'{"hits": 1}'


def test_dql_parallel_decodes_each_format():
    results = _mk(b"a,b\n").dql_parallel([{"query": "q", "format": "csv"}] * 2)
    assert results == ["a,b\n", "a,b\n"]


@pytest.mark.anyio
async def test_async_dql_formats():
    def adb(content):
        return DiffbotAsync(token="t", transport=httpx.MockTransport(lambda r: httpx.Response(200, content=content)))

    assert await adb(b"x\n").dql("q", format="csv") == "x\n"
    assert await adb(b"\x00\x01").dql("q", format="xlsx") == b"\x00\x01"
    assert await adb(b"x\n").dql("q", format="csv", raw=True) == b"x\n"
    entities = [e async for e in await adb(JSONL).dql("q", format="jsonl")]
    assert [e["score"] for e in entities] == [1, 2]
    assert await adb(JSONL).dql("q", format="jsonl", raw=True) == JSONL


"""
Named DQL options (S2)
"""

ALL_NAMED = dict(
    type="crawl", col="a,b", filter_exclude="skills.name", exportseparator="|", exportfile="out.csv",
    jsonmode="extended", non_canonical_facts=True, no_dedup_articles=True, cluster="best",
)
ALL_WIRE = {
    "type": "crawl", "col": "a,b", "filterExclude": "skills.name", "exportseparator": "|",
    "exportfile": "out.csv", "jsonmode": "extended", "nonCanonicalFacts": True,
    "noDedupArticles": True, "cluster": "best",
}


def test_dql_named_options_go_in_body_not_url():
    seen, handler = _capture()
    db = Diffbot(token="tok", transport=httpx.MockTransport(handler))
    db.dql("q", **ALL_NAMED)
    (req,) = seen
    assert dict(req.url.params) == {"token": "tok"}
    assert json.loads(req.content) == {"query": "q", "size": 10, **ALL_WIRE}


def test_dql_named_options_default_to_absent():
    seen, handler = _capture()
    db = Diffbot(token="t", transport=httpx.MockTransport(handler))
    db.dql("q")
    assert json.loads(seen[0].content) == {"query": "q", "size": 10}
    seen.clear()
    db.dql("q", non_canonical_facts=False, type="query")
    assert json.loads(seen[0].content) == {"query": "q", "size": 10, "nonCanonicalFacts": False, "type": "query"}


def test_dql_extra_collision_with_named_raises():
    seen, handler = _capture()
    db = Diffbot(token="t", transport=httpx.MockTransport(handler))
    with pytest.raises(ValidationError, match="jsonmode"):
        db.dql("q", jsonmode="id", extra={"jsonmode": "extended"})
    with pytest.raises(ValidationError, match="filterExclude"):
        db.dql("q", filter_exclude="a", extra={"filterExclude": "b"})
    assert seen == []


def test_dql_report_and_view_still_reachable_via_extra():
    seen, handler = _capture()
    db = Diffbot(token="t", transport=httpx.MockTransport(handler))
    db.dql("q", type="text", extra={"report": True, "view": "x"})
    assert json.loads(seen[0].content) == {"query": "q", "size": 10, "type": "text", "report": True, "view": "x"}


def test_dql_parallel_forwards_named_options():
    seen, handler = _capture()
    db = Diffbot(token="t", transport=httpx.MockTransport(handler))
    db.dql_parallel([{"query": "a", "type": "crawl", "col": "all"}])
    assert json.loads(seen[0].content) == {"query": "a", "size": 10, "type": "crawl", "col": "all"}


@pytest.mark.anyio
async def test_async_dql_named_options_go_in_body_not_url():
    seen, handler = _capture()
    db = DiffbotAsync(token="tok", transport=httpx.MockTransport(handler))
    await db.dql("q", **ALL_NAMED)
    (req,) = seen
    assert dict(req.url.params) == {"token": "tok"}
    assert json.loads(req.content) == {"query": "q", "size": 10, **ALL_WIRE}
    seen.clear()
    await db.dql("q")
    assert json.loads(seen[0].content) == {"query": "q", "size": 10}


@pytest.mark.anyio
async def test_async_dql_extra_collision_with_named_raises():
    seen, handler = _capture()
    db = DiffbotAsync(token="t", transport=httpx.MockTransport(handler))
    with pytest.raises(ValidationError, match="cluster"):
        await db.dql("q", cluster="all", extra={"cluster": "best"})
    assert seen == []


@pytest.mark.anyio
async def test_async_dql_parallel_forwards_named_options():
    seen, handler = _capture()
    db = DiffbotAsync(token="t", transport=httpx.MockTransport(handler))
    await db.dql_parallel([{"query": "a", "type": "crawl", "col": "all"}])
    assert json.loads(seen[0].content) == {"query": "a", "size": 10, "type": "crawl", "col": "all"}
