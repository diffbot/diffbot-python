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

"""
crawl_download (GET /v3/crawl/data) and the watcher that reuses it
"""

RECORDS = [{"type": "article", "title": "A", "pageUrl": "https://example.com/a"}]
URLS_CSV = 'Url,Crawl Status,Crawled Time\n"https://example.com/a",Successfully Crawled,2026-11-17\n'


def _data_handler(seen, *, json_body=None, text=None):
    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        if json_body is not None:
            return httpx.Response(200, json=json_body)
        return httpx.Response(200, text=text or "")

    return handler


def test_crawl_download_json_default():
    seen = []
    db = make_client(_data_handler(seen, json_body=RECORDS))
    assert db.crawl_download("job1") == RECORDS
    (req,) = seen
    assert req.method == "GET"
    assert req.url.path == "/v3/crawl/data"
    assert dict(req.url.params) == {"token": "test-token", "name": "job1"}


def test_crawl_download_csv_type_and_num():
    seen = []
    db = make_client(_data_handler(seen, text=URLS_CSV))
    out = db.crawl_download("job1", format="csv", type="urls", num=5)
    assert out == URLS_CSV
    assert dict(seen[0].url.params) == {
        "token": "test-token", "name": "job1", "format": "csv", "type": "urls", "num": "5",
    }


def test_crawl_download_empty_json_body_is_empty_list():
    assert make_client(_data_handler([], text="")).crawl_download("job1") == []


def test_crawl_download_follows_redirects():
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/v3/crawl/data":
            return httpx.Response(302, headers={"location": "https://files.example.com/out.json"})
        return httpx.Response(200, json=RECORDS)

    assert make_client(handler).crawl_download("job1") == RECORDS


def test_crawl_download_missing_job_raises_not_found():
    from diffbot import NotFoundError

    db = Diffbot(token="t", transport=httpx.MockTransport(lambda r: httpx.Response(404, text="no")), retry=False)
    with pytest.raises(NotFoundError):
        db.crawl_download("nope")


@pytest.mark.anyio
async def test_async_crawl_download():
    seen = []
    db = DiffbotAsync(token="test-token", transport=httpx.MockTransport(_data_handler(seen, json_body=RECORDS)))
    assert await db.crawl_download("job1", num=1) == RECORDS
    assert seen[0].url.params["num"] == "1"
    db2 = DiffbotAsync(token="test-token", transport=httpx.MockTransport(_data_handler([], text=URLS_CSV)))
    assert await db2.crawl_download("job1", format="csv") == URLS_CSV


def _watch_handler(seen):
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("/data"):
            seen.append(request)
            return httpx.Response(200, text=URLS_CSV)
        if "seeds" in request.url.params:
            return httpx.Response(200, json={"jobs": []})
        return httpx.Response(200, json={"jobs": [{"name": "j", "jobStatus": {"status": 9, "message": "done"}}]})

    return handler


def test_crawl_watch_uses_download_for_urls():
    seen = []
    events = list(make_client(_watch_handler(seen)).crawl("example.com", job_name="j", watch=True, poll_interval=0))
    urls = [e.details["url"] for e in events if e.event_type == CrawlEventType.URL_PROCESSED]
    assert urls == ["https://example.com/a"]
    assert seen[0].url.params["type"] == "urls"
    assert seen[0].url.params["format"] == "csv"


@pytest.mark.anyio
async def test_async_crawl_watch_uses_download_for_urls():
    seen = []
    db = DiffbotAsync(token="test-token", transport=httpx.MockTransport(_watch_handler(seen)))
    urls = [
        e.details["url"]
        async for e in db.crawl("example.com", job_name="j", watch=True, poll_interval=0)
        if e.event_type == CrawlEventType.URL_PROCESSED
    ]
    assert urls == ["https://example.com/a"]
    assert seen[0].url.params["type"] == "urls"


def test_crawl_get_job_missing_is_empty_dict():
    db = make_client(lambda r: httpx.Response(200, json={"jobs": []}))
    assert db.crawl_get_job("nope") == {}
