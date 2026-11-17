"""Exercises the code patterns shown in the README Usage and Async Usage sections."""
import json

import httpx
import pytest

from diffbot import CrawlEventType, Diffbot, DiffbotAsync, RetryPolicy, json_schema_format, resolve_token

SSE_PARIS = 'data: {"choices": [{"delta": {"content": "Paris"}}]}\n'

CAPITAL_SCHEMA = {
    "type": "object",
    "properties": {
        "country": {"type": "string"},
        "capital": {"type": "string"},
    },
    "required": ["country", "capital"],
}
SSE_CAPITAL_JSON = (
    "data: "
    + json.dumps({"choices": [{"delta": {"content": '{"country": "France", "capital": "Paris"}'}}]})
    + "\n"
)


# ---------------------------------------------------------------------------
# Client configuration
# ---------------------------------------------------------------------------

def test_readme_client_configuration_custom_dql_url():
    def handler(request: httpx.Request) -> httpx.Response:
        assert str(request.url).startswith("http://localhost:8080/kg/v3/dql")
        return httpx.Response(200, json={"data": [{"entity": {"name": "Diffbot"}}]})

    db = Diffbot(
        token="YOUR_TOKEN",
        timeout=60.0,
        dql_url="http://localhost:8080/kg/v3/dql",
        transport=httpx.MockTransport(handler),
    )
    results = db.dql('type:Organization name:"Diffbot"')
    assert "data" in results


def test_readme_client_configuration_transport():
    transport = httpx.HTTPTransport(retries=3)
    with Diffbot(token="YOUR_TOKEN", transport=transport) as db:
        assert db._http._transport is transport


def test_readme_client_configuration_api_base():
    staging = Diffbot(token="YOUR_TOKEN", api_base="https://staging.example.com")
    assert staging.analyze_url == "https://staging.example.com/v3"
    assert staging.crawler_url == "https://staging.example.com/v3/crawl"


def test_readme_client_configuration_retry():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(500, text="boom")

    db = Diffbot(token="YOUR_TOKEN", retry=False, transport=httpx.MockTransport(handler))
    with pytest.raises(Exception):
        db.extract("https://www.example.com")

    tuned = Diffbot(token="YOUR_TOKEN", retry=RetryPolicy(max_attempts=5))
    assert tuned._retry_policy.max_attempts == 5


# ---------------------------------------------------------------------------
# Sync Usage
# ---------------------------------------------------------------------------

def test_readme_sync_extract():
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.params["token"] == "test-token"
        assert request.url.params["url"] == "https://news.ycombinator.com"
        return httpx.Response(200, json={"objects": [{"title": "Hacker News"}]})

    db = Diffbot(token="test-token", transport=httpx.MockTransport(handler))
    data = db.extract("https://news.ycombinator.com")
    assert "objects" in data


def test_readme_sync_ask():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, text=SSE_PARIS)

    db = Diffbot(token="test-token", transport=httpx.MockTransport(handler))
    chunks = list(db.ask([{"role": "user", "content": "What's the capital of France?"}]))
    assert "Paris" in "".join(chunks)


def test_readme_sync_ask_json_with_schema():
    def handler(request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content)
        assert body["response_format"]["type"] == "json_schema"
        assert body["response_format"]["json_schema"]["schema"] == CAPITAL_SCHEMA
        return httpx.Response(200, text=SSE_CAPITAL_JSON)

    db = Diffbot(token="test-token", transport=httpx.MockTransport(handler))
    answer = db.ask_json(
        [{"role": "user", "content": "What's the capital of France?"}], CAPITAL_SCHEMA
    )
    assert answer["capital"] == "Paris"


def test_readme_sync_ask_json_without_schema():
    def handler(request: httpx.Request) -> httpx.Response:
        # Defaults to a permissive json_schema, never {"type": "json_object"}.
        fmt = json.loads(request.content)["response_format"]
        assert fmt["type"] == "json_schema"
        assert fmt["json_schema"]["schema"] == {"type": "object"}
        return httpx.Response(200, text=SSE_CAPITAL_JSON)

    db = Diffbot(token="test-token", transport=httpx.MockTransport(handler))
    answer = db.ask_json([{"role": "user", "content": "What's the capital of France?"}])
    assert answer["country"] == "France"


def test_readme_sync_ask_streaming_with_response_format():
    def handler(request: httpx.Request) -> httpx.Response:
        assert json.loads(request.content)["response_format"]["type"] == "json_schema"
        return httpx.Response(200, text=SSE_CAPITAL_JSON)

    db = Diffbot(token="test-token", transport=httpx.MockTransport(handler))
    chunks = list(
        db.ask(
            [{"role": "user", "content": "What's the capital of France?"}],
            response_format=json_schema_format(CAPITAL_SCHEMA),
        )
    )
    assert json.loads("".join(chunks))["capital"] == "Paris"


def test_readme_sync_crawl():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"jobs": [{"name": "test-job"}]})

    db = Diffbot(token="test-token", transport=httpx.MockTransport(handler))
    events = list(db.crawl("https://example.com", hops=1, job_name="test-job"))
    assert len(events) == 1
    assert events[0].event_type == CrawlEventType.JOB_CREATED


def test_readme_sync_dql():
    def handler(request: httpx.Request) -> httpx.Response:
        assert "Diffbot" in json.loads(request.content)["query"]
        return httpx.Response(200, json={"data": [{"entity": {"name": "Diffbot"}}]})

    db = Diffbot(token="test-token", transport=httpx.MockTransport(handler))
    results = db.dql('type:Organization name:"Diffbot"')
    assert "data" in results


# ---------------------------------------------------------------------------
# Async Usage
# ---------------------------------------------------------------------------

@pytest.mark.anyio
async def test_readme_async_extract():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"objects": [{"title": "Hacker News"}]})

    async with DiffbotAsync(token="test-token", transport=httpx.MockTransport(handler)) as db:
        data = await db.extract("https://news.ycombinator.com")
    assert "objects" in data


@pytest.mark.anyio
async def test_readme_async_ask():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, text=SSE_PARIS)

    async with DiffbotAsync(token="test-token", transport=httpx.MockTransport(handler)) as db:
        chunks = [chunk async for chunk in db.ask([{"role": "user", "content": "What's the capital of France?"}])]
    assert "Paris" in "".join(chunks)


@pytest.mark.anyio
async def test_readme_async_ask_json_with_schema():
    def handler(request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content)
        assert body["response_format"]["json_schema"]["schema"] == CAPITAL_SCHEMA
        return httpx.Response(200, text=SSE_CAPITAL_JSON)

    async with DiffbotAsync(token="test-token", transport=httpx.MockTransport(handler)) as db:
        answer = await db.ask_json(
            [{"role": "user", "content": "What's the capital of France?"}], CAPITAL_SCHEMA
        )
    assert answer["capital"] == "Paris"


@pytest.mark.anyio
async def test_readme_async_crawl():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"jobs": [{"name": "test-job"}]})

    async with DiffbotAsync(token="test-token", transport=httpx.MockTransport(handler)) as db:
        events = [event async for event in db.crawl("https://example.com", hops=1, job_name="test-job")]
    assert len(events) == 1
    assert events[0].event_type == CrawlEventType.JOB_CREATED


@pytest.mark.anyio
async def test_readme_async_dql():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"data": [{"entity": {"name": "Diffbot"}}]})

    async with DiffbotAsync(token="test-token", transport=httpx.MockTransport(handler)) as db:
        results = await db.dql('type:Organization name:"Diffbot"')
    assert "data" in results


def test_readme_sync_web_search():
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.headers["Authorization"] == "Bearer test-token"
        assert request.url.params["text"] == "diffbot knowledge graph"
        return httpx.Response(200, json={
            "query": ["diffbot knowledge graph"],
            "search_results": [{"score": 0.95, "title": "Diffbot", "pageUrl": "https://diffbot.com", "content": "AI-powered web data."}],
            "timeMs": 10,
        })

    db = Diffbot(token="test-token", transport=httpx.MockTransport(handler))
    results = db.web_search("diffbot knowledge graph")
    assert len(results["search_results"]) == 1
    r = results["search_results"][0]
    assert r["title"] == "Diffbot"
    assert r["content"] == "AI-powered web data."


@pytest.mark.anyio
async def test_readme_async_web_search():
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.headers["Authorization"] == "Bearer test-token"
        assert request.url.params["text"] == "diffbot knowledge graph"
        return httpx.Response(200, json={
            "query": ["diffbot knowledge graph"],
            "search_results": [{"score": 0.95, "title": "Diffbot", "pageUrl": "https://diffbot.com", "content": "AI-powered web data."}],
            "timeMs": 10,
        })

    async with DiffbotAsync(token="test-token", transport=httpx.MockTransport(handler)) as db:
        results = await db.web_search("diffbot knowledge graph")
    assert len(results["search_results"]) == 1
    r = results["search_results"][0]
    assert r["title"] == "Diffbot"
    assert r["content"] == "AI-powered web data."


NLP_RESPONSE = [
    {
        "entities": [
            {"name": "Apple", "allTypes": [{"name": "organization"}], "id": "Cz9nk", "confidence": 0.98, "salience": 0.7, "sentiment": 0.0},
            {"name": "Tim Cook", "allTypes": [{"name": "person"}], "id": "Cv9nk", "confidence": 0.95, "salience": 0.5, "sentiment": 0.2},
        ],
        "sentiment": 0.3,
    }
]


def test_readme_sync_entities():
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.method == "POST"
        assert request.url.params["token"] == "test-token"
        assert "entities" in request.url.params["fields"]
        assert "sentiment" in request.url.params["fields"]
        return httpx.Response(200, json=NLP_RESPONSE)

    db = Diffbot(token="test-token", transport=httpx.MockTransport(handler))
    result = db.entities("Apple CEO Tim Cook announced record quarterly earnings.")
    assert len(result["entities"]) == 2
    assert result["entities"][0]["name"] == "Apple"
    assert result["sentiment"] == 0.3


@pytest.mark.anyio
async def test_readme_async_entities():
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.method == "POST"
        assert request.url.params["token"] == "test-token"
        assert "entities" in request.url.params["fields"]
        assert "sentiment" in request.url.params["fields"]
        return httpx.Response(200, json=NLP_RESPONSE)

    async with DiffbotAsync(token="test-token", transport=httpx.MockTransport(handler)) as db:
        result = await db.entities("Apple CEO Tim Cook announced record quarterly earnings.")
    assert len(result["entities"]) == 2
    assert result["entities"][0]["name"] == "Apple"
    assert result["sentiment"] == 0.3


# ---------------------------------------------------------------------------
# Authentication
# ---------------------------------------------------------------------------

def test_readme_authentication_resolve_token(monkeypatch, tmp_path):
    # README "Authentication": Diffbot(token=resolve_token()) using the env var.
    monkeypatch.setenv("DIFFBOT_API_TOKEN", "test-token")
    monkeypatch.setattr("diffbot._auth.CREDENTIALS_PATH", tmp_path / "missing")

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.params["token"] == "test-token"
        return httpx.Response(200, json={"objects": [{"title": "Example"}]})

    db = Diffbot(token=resolve_token(), transport=httpx.MockTransport(handler))
    data = db.extract("https://www.example.com")
    assert "objects" in data


# ---------------------------------------------------------------------------
# Extract options, DQL formats, crawl start/poll/download, account
# ---------------------------------------------------------------------------

def test_readme_sync_extract_options():
    def handler(request: httpx.Request) -> httpx.Response:
        params = request.url.params
        assert request.url.path == "/v3/article"
        assert params["timeout"] == "60000"
        assert params["fields"] == "links,quotes"
        assert params["maxTags"] == "5"
        assert "mode" not in params  # fmt="json" -> no llm mapping
        assert request.extensions["timeout"]["read"] == 70
        return httpx.Response(200, json={"objects": [{"title": "Post"}]})

    db = Diffbot(token="test-token", transport=httpx.MockTransport(handler))
    article = db.extract(
        "https://www.example.com/post",
        "article",
        fmt="json",
        timeout=60000,
        fields=["links", "quotes"],
        max_tags=5,
    )
    assert article["objects"][0]["title"] == "Post"


def test_readme_sync_dql_formats():
    def handler(request: httpx.Request) -> httpx.Response:
        fmt = json.loads(request.content)["format"]
        if fmt == "csv":
            return httpx.Response(200, text="name\nDiffbot\n")
        return httpx.Response(200, text='{"entity": {"name": "Diffbot"}}\n')

    db = Diffbot(token="test-token", transport=httpx.MockTransport(handler))
    csv_text = db.dql('type:Organization name:"Diffbot"', size=5, format="csv")
    assert csv_text == "name\nDiffbot\n"
    names = [e["entity"]["name"] for e in db.dql('type:Organization name:"Diffbot"', size=5, format="jsonl")]
    assert names == ["Diffbot"]


def _crawl_flow_handler(request: httpx.Request) -> httpx.Response:
    if request.url.path == "/v3/crawl/data":
        if request.url.params.get("format") == "csv":
            return httpx.Response(200, text="Url\nhttps://www.example.com\n")
        return httpx.Response(200, json=[{"pageUrl": "https://www.example.com"}])
    if "seeds" in request.url.params:
        return httpx.Response(200, json={"jobs": [{"name": "my-crawl"}]})
    return httpx.Response(200, json={"jobs": [{"name": "my-crawl", "jobStatus": {"status": 9}}]})


def test_readme_sync_crawl_start_poll_download():
    db = Diffbot(token="test-token", transport=httpx.MockTransport(_crawl_flow_handler))
    for _ in db.crawl("https://www.example.com", job_name="my-crawl", hops=1):
        pass
    while db.crawl_get_job("my-crawl").get("jobStatus", {}).get("status", 0) in (0, 7):
        raise AssertionError("job should already be complete")
    records = db.crawl_download("my-crawl")
    csv_text = db.crawl_download("my-crawl", format="csv")
    assert records == [{"pageUrl": "https://www.example.com"}]
    assert csv_text.startswith("Url")
    assert db.crawl_get_job.__doc__ and "{}" in db.crawl_get_job.__doc__


def test_readme_sync_account_and_verify_token():
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/v4/account"
        return httpx.Response(200, json={"usage": [{"date": "2026-11-16", "credits": 1}]})

    db = Diffbot(token="test-token", transport=httpx.MockTransport(handler))
    assert db.verify_token()
    usage = db.account(days=7).get("usage", [])
    assert usage[0]["credits"] == 1


@pytest.mark.anyio
async def test_readme_async_extract_options():
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.params["fields"] == "links"
        return httpx.Response(200, json={"objects": []})

    async with DiffbotAsync(token="test-token", transport=httpx.MockTransport(handler)) as db:
        await db.extract("https://www.example.com", "article", fmt="json", timeout=60000, fields=["links"])


@pytest.mark.anyio
async def test_readme_async_dql_formats():
    def handler(request: httpx.Request) -> httpx.Response:
        if json.loads(request.content)["format"] == "csv":
            return httpx.Response(200, text="name\nDiffbot\n")
        return httpx.Response(200, text='{"entity": {"name": "Diffbot"}}\n')

    async with DiffbotAsync(token="test-token", transport=httpx.MockTransport(handler)) as db:
        csv_text = await db.dql('type:Organization name:"Diffbot"', size=5, format="csv")
        names = [e["entity"]["name"] async for e in await db.dql('type:Organization name:"Diffbot"', size=5, format="jsonl")]
    assert csv_text == "name\nDiffbot\n"
    assert names == ["Diffbot"]


@pytest.mark.anyio
async def test_readme_async_crawl_start_poll_download():
    async with DiffbotAsync(token="test-token", transport=httpx.MockTransport(_crawl_flow_handler)) as db:
        async for _ in db.crawl("https://www.example.com", job_name="my-crawl", hops=1):
            pass
        while (await db.crawl_get_job("my-crawl")).get("jobStatus", {}).get("status", 0) in (0, 7):
            raise AssertionError("job should already be complete")
        records = await db.crawl_download("my-crawl")
        csv_text = await db.crawl_download("my-crawl", format="csv")
    assert records == [{"pageUrl": "https://www.example.com"}]
    assert csv_text.startswith("Url")


@pytest.mark.anyio
async def test_readme_async_account_and_verify_token():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"usage": []})

    async with DiffbotAsync(token="test-token", transport=httpx.MockTransport(handler)) as db:
        assert await db.verify_token()
        usage = (await db.account(days=7)).get("usage", [])
    assert usage == []
