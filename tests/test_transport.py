import httpx
import pytest

from diffbot import APIError, AuthError, Diffbot, DiffbotAsync, NotFoundError, RateLimitError, RetryPolicy
from diffbot._transport import raise_for_status


def make_client(handler, **kwargs) -> Diffbot:
    return Diffbot(token="test-token", transport=httpx.MockTransport(handler), **kwargs)


"""
Repeated query parameters
"""


def test_request_appends_array_valued_params_instead_of_overwriting():
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.params.get_list("tag") == ["a", "b", "c"]
        return httpx.Response(200, json={})

    db = make_client(handler)
    db.request("GET", "https://example.com/x", params={"tag": ["a", "b", "c"]})


"""
DELETE, raw and form bodies
"""


def test_request_issues_a_delete_with_a_json_body():
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.method == "DELETE"
        assert request.headers["content-type"] == "application/json"
        assert request.content == b'{"api":"x"}'
        return httpx.Response(200, json={})

    db = make_client(handler)
    db.request("DELETE", "https://example.com/custom", json={"api": "x"})


def test_request_form_encodes_a_data_body_and_sets_content_type():
    def handler(request: httpx.Request) -> httpx.Response:
        assert "application/x-www-form-urlencoded" in request.headers["content-type"]
        assert request.content == b"a=1&b=2"
        return httpx.Response(200, json={})

    db = make_client(handler)
    db.request("POST", "https://example.com/x", data={"a": "1", "b": "2"})


def test_request_lets_a_caller_override_content_type_with_a_raw_body():
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.headers["content-type"] == "text/html"
        assert request.content == b"<html></html>"
        return httpx.Response(200, json={})

    db = make_client(handler)
    db.request(
        "POST",
        "https://example.com/x",
        content="<html></html>",
        headers={"Content-Type": "text/html"},
    )


"""
Per-call timeout
"""


def test_request_per_call_timeout_overrides_the_client_default():
    captured = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["timeout"] = request.extensions.get("timeout")
        return httpx.Response(200, json={})

    db = make_client(handler, timeout=30.0)
    db.request("GET", "https://example.com/x", timeout=5.0)
    assert captured["timeout"]["read"] == 5.0


"""
Retry policy
"""


def test_retries_a_429_and_honors_a_numeric_retry_after():
    calls = {"n": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        calls["n"] += 1
        if calls["n"] == 1:
            return httpx.Response(429, headers={"retry-after": "0"})
        return httpx.Response(200, json={"ok": True})

    db = make_client(handler, retry=RetryPolicy(base_delay=0.001, max_delay=0.001))
    response = db.request("GET", "https://example.com/x")
    assert calls["n"] == 2
    assert response.status_code == 200


def test_retries_5xx_responses():
    calls = {"n": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        calls["n"] += 1
        if calls["n"] == 1:
            return httpx.Response(503)
        return httpx.Response(200, json={"ok": True})

    db = make_client(handler, retry=RetryPolicy(base_delay=0.001, max_delay=0.001))
    response = db.request("GET", "https://example.com/x")
    assert calls["n"] == 2
    assert response.status_code == 200


def test_retries_connection_errors():
    calls = {"n": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        calls["n"] += 1
        if calls["n"] == 1:
            raise httpx.ConnectError("boom")
        return httpx.Response(200, json={"ok": True})

    db = make_client(handler, retry=RetryPolicy(base_delay=0.001, max_delay=0.001))
    response = db.request("GET", "https://example.com/x")
    assert calls["n"] == 2
    assert response.status_code == 200


def test_gives_up_after_max_attempts():
    calls = {"n": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        calls["n"] += 1
        return httpx.Response(500)

    db = make_client(handler, retry=RetryPolicy(max_attempts=2, base_delay=0.001, max_delay=0.001))
    with pytest.raises(APIError):
        db.request("GET", "https://example.com/x")
    assert calls["n"] == 2


def test_does_not_retry_a_call_marked_retryable_false():
    calls = {"n": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        calls["n"] += 1
        return httpx.Response(503)

    db = make_client(handler, retry=RetryPolicy(base_delay=0.001, max_delay=0.001))
    with pytest.raises(APIError):
        db.request("GET", "https://example.com/x", retryable=False)
    assert calls["n"] == 1


def test_does_not_retry_at_all_when_retry_is_disabled_client_wide():
    calls = {"n": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        calls["n"] += 1
        return httpx.Response(500)

    db = make_client(handler, retry=False)
    with pytest.raises(APIError):
        db.request("GET", "https://example.com/x")
    assert calls["n"] == 1


def test_does_not_retry_a_4xx_that_isnt_429():
    calls = {"n": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        calls["n"] += 1
        return httpx.Response(400)

    db = make_client(handler, retry=RetryPolicy(base_delay=0.001, max_delay=0.001))
    with pytest.raises(APIError):
        db.request("GET", "https://example.com/x")
    assert calls["n"] == 1


@pytest.mark.anyio
async def test_async_retries_a_429():
    calls = {"n": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        calls["n"] += 1
        if calls["n"] == 1:
            return httpx.Response(429, headers={"retry-after": "0"})
        return httpx.Response(200, json={"ok": True})

    db = DiffbotAsync(
        token="test-token",
        transport=httpx.MockTransport(handler),
        retry=RetryPolicy(base_delay=0.001, max_delay=0.001),
    )
    response = await db.request("GET", "https://example.com/x")
    assert calls["n"] == 2
    assert response.status_code == 200


"""
raise_for_status
"""


def test_raise_for_status_throws_not_found_error_for_a_404_and_attaches_headers():
    response = httpx.Response(404, headers={"X-Test": "1"})
    with pytest.raises(NotFoundError) as exc_info:
        raise_for_status(response)
    assert exc_info.value.headers.get("x-test") == "1"


def test_raise_for_status_is_a_noop_for_an_ok_response():
    raise_for_status(httpx.Response(200))


def test_raise_for_status_throws_auth_error_for_401():
    with pytest.raises(AuthError):
        raise_for_status(httpx.Response(401))


def test_raise_for_status_throws_rate_limit_error_for_429_with_retry_after():
    response = httpx.Response(429, headers={"retry-after": "7"})
    with pytest.raises(RateLimitError) as exc_info:
        raise_for_status(response)
    assert exc_info.value.retry_after == "7"
