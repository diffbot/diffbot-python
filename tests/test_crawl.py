import httpx
import pytest

from diffbot import APIError, AuthError, Diffbot, DiffbotAsync, JobError, RateLimitError
from diffbot import CrawlEvent, CrawlEventType


def make_client(handler) -> Diffbot:
    return Diffbot(token="test-token", transport=httpx.MockTransport(handler))


def test_crawl_returns_job_created_event():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"response": "Successfully added urls for spidering.", "jobs": [{"name": "test-job"}]})

    db = make_client(handler)
    event = next(db.crawl("https://example.com", job_name="test-job"))
    assert event.event_type == CrawlEventType.JOB_CREATED
    assert event.details["job_name"] == "test-job"


def test_crawl_sends_token_and_seeds():
    captured = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["params"] = dict(request.url.params)
        return httpx.Response(200, json={"jobs": [{"name": "test-job"}]})

    db = make_client(handler)
    next(db.crawl("https://example.com", job_name="test-job"))
    assert captured["params"]["token"] == "test-token"
    assert captured["params"]["seeds"] == "https://example.com"


def test_crawl_normalizes_url():
    captured = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["seeds"] = request.url.params["seeds"]
        return httpx.Response(200, json={"jobs": [{"name": "test-job"}]})

    db = make_client(handler)
    next(db.crawl("example.com", job_name="test-job"))
    assert captured["seeds"] == "https://example.com"


def test_crawl_auth_error():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(401, json={
            "code": 401,
            "message": "Unauthorized",
            "requestId": "123456789",
            "error": "Not authorized API token.",
            "errorCode": 401,
        })

    db = make_client(handler)
    with pytest.raises(AuthError) as exc_info:
        next(db.crawl("https://example.com"))
    err = exc_info.value
    assert err.status_code == 401
    assert err.message == "Unauthorized"
    assert err.request_id == "123456789"


"""
Job failure -> JobError (not a synthesized APIError(500, ...))
"""


def test_crawl_watch_raises_job_error_on_failed_status():
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("/data"):
            return httpx.Response(200, text="")
        if "seeds" in request.url.params:
            return httpx.Response(200, json={"jobs": [{"name": "test-job"}]})
        return httpx.Response(
            200,
            json={"jobs": [{"name": "test-job", "jobStatus": {"status": 9, "message": "Crawl failed: bad seed"}}]},
        )

    db = make_client(handler)
    with pytest.raises(JobError) as exc_info:
        list(db.crawl("https://example.com", job_name="test-job", watch=True, poll_interval=0))
    assert isinstance(exc_info.value, APIError)
    assert exc_info.value.job_name == "test-job"
    assert "bad seed" in str(exc_info.value)


@pytest.mark.anyio
async def test_async_crawl_watch_raises_job_error_on_failed_status():
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("/data"):
            return httpx.Response(200, text="")
        if "seeds" in request.url.params:
            return httpx.Response(200, json={"jobs": [{"name": "test-job"}]})
        return httpx.Response(
            200,
            json={"jobs": [{"name": "test-job", "jobStatus": {"status": 9, "message": "Crawl failed: bad seed"}}]},
        )

    db = DiffbotAsync(token="test-token", transport=httpx.MockTransport(handler))
    with pytest.raises(JobError) as exc_info:
        events = []
        async for event in db.crawl("https://example.com", job_name="test-job", watch=True, poll_interval=0):
            events.append(event)
    assert exc_info.value.job_name == "test-job"


"""
crawl_delete_job is a GET-shaped mutation and must not be retried
"""


def test_crawl_delete_job_is_not_retried():
    calls = {"n": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        calls["n"] += 1
        return httpx.Response(503)

    from diffbot import RetryPolicy

    db = Diffbot(
        token="test-token",
        retry=RetryPolicy(base_delay=0.001, max_delay=0.001),
        transport=httpx.MockTransport(handler),
    )
    with pytest.raises(APIError):
        db.crawl_delete_job("test-job")
    assert calls["n"] == 1