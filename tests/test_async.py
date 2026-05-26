import httpx
import pytest

from diffbot import AuthError, DiffbotAsync
from diffbot import CrawlEventType


def make_async_client(handler) -> DiffbotAsync:
    return DiffbotAsync(token="test-token", transport=httpx.MockTransport(handler))


@pytest.mark.anyio
async def test_async_extract_returns_dict():
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.params["token"] == "test-token"
        assert request.url.params["url"] == "https://example.com"
        return httpx.Response(200, json={"objects": [{"title": "Example"}]})

    db = make_async_client(handler)
    result = await db.extract("https://example.com")
    assert result == {"objects": [{"title": "Example"}]}


@pytest.mark.anyio
async def test_async_crawl_returns_job_created():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"jobs": [{"name": "test-job"}]})

    db = make_async_client(handler)
    events = [event async for event in db.crawl("https://example.com", job_name="test-job")]
    assert len(events) == 1
    assert events[0].event_type == CrawlEventType.JOB_CREATED
    assert events[0].details["job_name"] == "test-job"


@pytest.mark.anyio
async def test_async_context_manager_closes_client():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={})

    async with DiffbotAsync(token="t", transport=httpx.MockTransport(handler)) as db:
        await db.extract("example.com")
    assert db._http.is_closed


@pytest.mark.anyio
async def test_async_auth_error():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(401, json={
            "code": 401,
            "message": "Unauthorized",
            "requestId": "123456789",
            "error": "Not authorized API token.",
            "errorCode": 401,
        })

    db = make_async_client(handler)
    with pytest.raises(AuthError) as exc_info:
        await db.extract("https://example.com")
    err = exc_info.value
    assert err.status_code == 401
    assert err.message == "Unauthorized"
    assert err.request_id == "123456789"


"""
Live
"""

@pytest.mark.live
@pytest.mark.anyio
async def test_live_async_extract(live_token):
    async with DiffbotAsync(token=live_token) as db:
        result = await db.extract("https://example.com")
    assert "objects" in result
    assert len(result["objects"]) > 0
    assert "content" in result["objects"][0]


@pytest.mark.live
@pytest.mark.anyio
async def test_live_async_dql(live_token):
    async with DiffbotAsync(token=live_token) as db:
        result = await db.dql('type:Organization name:"Diffbot"', size=1)
    assert "data" in result
    assert len(result["data"]) > 0


@pytest.mark.live
@pytest.mark.anyio
async def test_live_async_web_search(live_token):
    async with DiffbotAsync(token=live_token) as db:
        result = await db.web_search("diffbot knowledge graph", num_results=3)
    assert "search_results" in result
