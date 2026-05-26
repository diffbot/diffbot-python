import httpx
import pytest

from diffbot import APIError, AuthError, Diffbot, ExtractionError, RateLimitError, ValidationError


"""
Client Errors
"""

def make_client(handler) -> Diffbot:
    return Diffbot(token="test-token", transport=httpx.MockTransport(handler))


def test_extract_returns_raw_dict():
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.params["token"] == "test-token"
        assert request.url.params["url"] == "https://example.com"
        return httpx.Response(200, json={"objects": [{"title": "Example", "pageUrl": "https://example.com"}]})

    db = make_client(handler)
    result = db.extract("https://example.com")
    assert result == {"objects": [{"title": "Example", "pageUrl": "https://example.com"}]}


def test_extract_normalizes_url():
    captured = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["url"] = request.url.params["url"]
        return httpx.Response(200, json={"objects": []})

    db = make_client(handler)
    db.extract("example.com")
    assert captured["url"] == "https://example.com"


def test_token_required():
    with pytest.raises(ValidationError):
        Diffbot(token="")


def test_user_agent_header():
    captured = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["ua"] = request.headers.get("user-agent")
        return httpx.Response(200, json={})

    db = make_client(handler)
    db.extract("example.com")
    assert captured["ua"].startswith("diffbot-python/")


def test_auth_error():
    def handler(request):
        return httpx.Response(401, json={
            "code": 401,
            "message": "Unauthorized. Incorrect token.",
            "requestId": "123456789",
        })

    db = make_client(handler)
    with pytest.raises(AuthError) as exc_info:
        db.extract("example.com")
    err = exc_info.value
    assert err.status_code == 401
    assert err.message == "Unauthorized. Incorrect token."
    assert err.request_id == "123456789"
    assert "Unauthorized. Incorrect token." in str(err)


def test_context_manager_closes_client():
    def handler(request):
        return httpx.Response(200, json={})

    with Diffbot(token="t", transport=httpx.MockTransport(handler)) as db:
        db.extract("example.com")
    assert db._http.is_closed

"""
Extraction Errors
 - These are errors that occur while attempting to fetch and/or extract the URL.
 - Always returns 200 from Extract API, extraction errors are passed in through the JSON response.
"""

def test_extraction_error_on_fetch_failure():
    # https://docs.diffbot.com/reference/error-could-not-download-page
    def handler(request):
        return httpx.Response(200, json={"errorCode": 500, "error": "Could not download page (403)"})

    db = make_client(handler)
    with pytest.raises(ExtractionError) as exc_info:
        db.extract("example.com")
    assert exc_info.value.error_code == 500
    assert "403" in exc_info.value.error


def test_extraction_error_on_page_not_found():
    # https://docs.diffbot.com/reference/error-could-not-download-page
    def handler(request):
        return httpx.Response(200, json={"errorCode": 404, "error": "Could not download page (404)"})

    db = make_client(handler)
    with pytest.raises(ExtractionError) as exc_info:
        db.extract("example.com")
    assert exc_info.value.error_code == 404
    assert exc_info.value.error == "Could not download page (404)"


def test_extraction_error_on_invalid_api():
    # https://docs.diffbot.com/reference/error-457-invalid-api
    def handler(request):
        return httpx.Response(200, json={"errorCode": 457, "error": "Invalid API. Make sure the api is valid. Check that it does not contain any unnecessary trailing backslashes."})

    db = make_client(handler)
    with pytest.raises(ExtractionError) as exc_info:
        db.extract("example.com")
    assert exc_info.value.error_code == 457
    assert exc_info.value.error == "Invalid API. Make sure the api is valid. Check that it does not contain any unnecessary trailing backslashes."


"""
Live
"""

@pytest.mark.live
def test_live_extract(db):
    result = db.extract("https://example.com")
    assert "objects" in result
    assert len(result["objects"]) > 0
    assert "content" in result["objects"][0]