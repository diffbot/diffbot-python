"""Exercises the code patterns shown in the README Usage and Async Usage sections."""
import httpx
import pytest

from diffbot import CrawlEventType, Diffbot, DiffbotAsync

SSE_PARIS = 'data: {"choices": [{"delta": {"content": "Paris"}}]}\n'


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


def test_readme_sync_crawl():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"jobs": [{"name": "test-job"}]})

    db = Diffbot(token="test-token", transport=httpx.MockTransport(handler))
    events = list(db.crawl("https://example.com", hops=1, job_name="test-job"))
    assert len(events) == 1
    assert events[0].event_type == CrawlEventType.JOB_CREATED


def test_readme_sync_dql():
    def handler(request: httpx.Request) -> httpx.Response:
        assert "Diffbot" in request.url.params["query"]
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
