import httpx
import pytest

from diffbot import APIError, AuthError, Diffbot, RateLimitError
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