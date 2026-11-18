import httpx
import pytest

from diffbot import (
    APIError,
    AuthError,
    Diffbot,
    DiffbotAsync,
    ExtractionError,
    RateLimitError,
    ValidationError,
    resolve_token,
)


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


def test_resolve_token_explicit_wins(monkeypatch, tmp_path):
    # An explicit token takes precedence over env var and file.
    monkeypatch.setenv("DIFFBOT_API_TOKEN", "env-token")
    assert resolve_token("explicit-token") == "explicit-token"


def test_resolve_token_from_env(monkeypatch, tmp_path):
    # A token in the environment is returned when none is passed.
    monkeypatch.setenv("DIFFBOT_API_TOKEN", "env-token")
    monkeypatch.setattr("diffbot._auth.CREDENTIALS_PATH", tmp_path / "missing")
    assert resolve_token() == "env-token"
    # And can be used to build a client.
    assert Diffbot(token=resolve_token()).token == "env-token"


def test_resolve_token_from_credentials_file(monkeypatch, tmp_path):
    # Falls back to ~/.diffbot/credentials when no env var is set.
    monkeypatch.delenv("DIFFBOT_API_TOKEN", raising=False)
    creds = tmp_path / "credentials"
    creds.write_text("DIFFBOT_API_TOKEN=file-token\n")
    monkeypatch.setattr("diffbot._auth.CREDENTIALS_PATH", creds)
    assert resolve_token() == "file-token"


def test_resolve_token_missing_returns_empty(monkeypatch, tmp_path):
    monkeypatch.delenv("DIFFBOT_API_TOKEN", raising=False)
    monkeypatch.setattr("diffbot._auth.CREDENTIALS_PATH", tmp_path / "missing")
    assert resolve_token() == ""


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

"""
Caller-set options (additive keyword-only args after fmt)
"""


def _capture_client(**kw):
    seen = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return httpx.Response(200, json={"objects": []})

    return seen, Diffbot(token="test-token", transport=httpx.MockTransport(handler), **kw)


def test_extract_defaults_unchanged():
    seen, db = _capture_client()
    db.extract("example.com")
    assert dict(seen[0].url.params) == {"token": "test-token", "url": "https://example.com", "timeout": "30000", "mode": "llm"}


def test_extract_wire_names_and_encoding():
    seen, db = _capture_client()
    db.extract(
        "example.com",
        "article",
        fmt="json",
        timeout=45000,
        fields=["links", "quotes"],
        discussion=False,
        paging=True,
        max_tags=3,
        tag_confidence=0.7,
        category_confidence=0.6,
        natural_language=["entities", "summary"],
        summary_num_sentences=2,
        use_proxy="default",
    )
    params = dict(seen[0].url.params)
    assert params == {
        "token": "test-token", "url": "https://example.com", "timeout": "45000",
        "fields": "links,quotes", "discussion": "false", "paging": "true", "maxTags": "3",
        "tagConfidence": "0.7", "categoryConfidence": "0.6", "naturalLanguage": "entities,summary",
        "summaryNumSentences": "2", "useProxy": "default",
    }


def test_extract_discussion_max_pages_and_analyze_fallback():
    seen, db = _capture_client()
    db.extract("example.com", "discussion", max_pages="all")
    assert seen[0].url.params["maxPages"] == "all"
    db.extract("example.com", fallback="article", mode="product")
    assert seen[1].url.params["fallback"] == "article"


def test_extract_mode_overrides_markdown_mapping():
    seen, db = _capture_client()
    db.extract("example.com", mode="article")  # fmt defaults to markdown
    assert seen[0].url.params["mode"] == "article"
    db.extract("example.com")
    assert seen[1].url.params["mode"] == "llm"


def test_extract_none_options_are_not_sent():
    seen, db = _capture_client()
    db.extract("example.com", fmt="json", fields=None, timeout=None)
    assert "fields" not in seen[0].url.params
    assert seen[0].url.params["timeout"] == "30000"


def test_extract_extra_passes_through_and_rejects_collisions():
    seen, db = _capture_client()
    db.extract("example.com", extra={"proxy": "1.2.3.4:80", "proxyAuth": "u:p"})
    assert seen[0].url.params["proxy"] == "1.2.3.4:80"
    assert seen[0].url.params["proxyAuth"] == "u:p"
    for bad in ({"token": "x"}, {"url": "x"}, {"maxPages": "2"}, {"timeout": 1}):
        with pytest.raises(ValidationError):
            db.extract("example.com", extra=bad)


def test_extract_unknown_option_is_type_error():
    _, db = _capture_client()
    with pytest.raises(TypeError):
        db.extract("example.com", bogus=1)


def _read_timeout(request: httpx.Request) -> float:
    return request.extensions["timeout"]["read"]


def test_transport_timeout_is_raised_above_a_long_caller_timeout():
    seen, db = _capture_client(timeout=30)
    db.extract("example.com", timeout=60000)
    assert seen[0].url.params["timeout"] == "60000"  # server-side, ms
    assert _read_timeout(seen[0]) == 70  # transport (s) = timeout + 10


def test_transport_timeout_is_never_lowered_by_a_short_caller_timeout():
    seen, db = _capture_client(timeout=120)
    db.extract("example.com", timeout=5000)
    assert seen[0].url.params["timeout"] == "5000"
    assert _read_timeout(seen[0]) == 120  # client default kept; 5s + 10s < 120s


def test_transport_timeout_untouched_without_caller_timeout():
    seen, db = _capture_client(timeout=30)
    db.extract("example.com")
    assert _read_timeout(seen[0]) == 30


@pytest.mark.anyio
async def test_async_extract_options_and_timeouts():
    seen = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return httpx.Response(200, json={"objects": []})

    db = DiffbotAsync(token="test-token", timeout=30, transport=httpx.MockTransport(handler))
    await db.extract("example.com", "article", fmt="json", fields=["links"], max_tags=2, timeout=60000)
    assert seen[0].url.params["fields"] == "links"
    assert seen[0].url.params["maxTags"] == "2"
    assert _read_timeout(seen[0]) == 70
    db2 = DiffbotAsync(token="test-token", timeout=120, transport=httpx.MockTransport(handler))
    await db2.extract("example.com", timeout=5000)
    assert _read_timeout(seen[1]) == 120
    with pytest.raises(ValidationError):
        await db2.extract("example.com", extra={"token": "x"})
