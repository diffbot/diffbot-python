import json

import httpx
import pytest

from diffbot import AuthError, Diffbot, DiffbotAsync, RateLimitError, json_schema_format
from diffbot.ask import (
    ANY_OBJECT_SCHEMA,
    _build_payload,
    _check_tool_call_leak,
    _extract_json,
    _resolve_format,
    _validate_response_format,
)
from diffbot.errors import ValidationError


class _FakeClient:
    token = "test-token"


CITY_SCHEMA = {
    "type": "object",
    "properties": {"country": {"type": "string"}, "capital": {"type": "string"}},
    "required": ["country", "capital"],
}


"""
json_schema_format
"""


def test_json_schema_format_nests_schema_correctly():
    # The server only honours the constraint when it finds json_schema.schema.
    fmt = json_schema_format(CITY_SCHEMA)
    assert fmt["type"] == "json_schema"
    assert fmt["json_schema"]["schema"] == CITY_SCHEMA
    assert fmt["json_schema"]["name"] == "response"


def test_json_schema_format_custom_name():
    assert json_schema_format(CITY_SCHEMA, name="city")["json_schema"]["name"] == "city"


def test_json_schema_format_rejects_non_dict():
    with pytest.raises(ValidationError):
        json_schema_format("not a schema")


"""
Validation
"""


def test_validate_allows_none_and_known_types():
    _validate_response_format(None)
    _validate_response_format({"type": "text"})
    _validate_response_format({"type": "json_object"})
    _validate_response_format(json_schema_format(CITY_SCHEMA))


def test_validate_rejects_unknown_type():
    with pytest.raises(ValidationError, match="text, json_object, json_schema"):
        _validate_response_format({"type": "nope"})


def test_validate_rejects_json_schema_without_nested_schema():
    # Server-side this returns 200 and silently ignores the constraint.
    with pytest.raises(ValidationError, match="json_schema"):
        _validate_response_format({"type": "json_schema", "json_schema": CITY_SCHEMA})


def test_validate_rejects_json_schema_with_no_json_schema_key():
    with pytest.raises(ValidationError):
        _validate_response_format({"type": "json_schema"})


def test_validate_rejects_non_dict():
    with pytest.raises(ValidationError):
        _validate_response_format("json")


"""
Payload
"""


def test_payload_omits_response_format_when_unset():
    _, payload = _build_payload(_FakeClient(), [{"role": "user", "content": "hi"}])
    assert "response_format" not in payload
    assert payload["stream"] is True


def test_payload_includes_response_format():
    fmt = json_schema_format(CITY_SCHEMA)
    headers, payload = _build_payload(_FakeClient(), [{"role": "user", "content": "hi"}], response_format=fmt)
    assert payload["response_format"] == fmt
    assert headers["Authorization"] == "Bearer test-token"


def test_payload_validates_before_sending():
    with pytest.raises(ValidationError):
        _build_payload(_FakeClient(), [], response_format={"type": "json_schema", "json_schema": {}})


"""
Format resolution
"""


def test_resolve_format_defaults_to_permissive_schema():
    # Deliberately not {"type": "json_object"} -- that mode has no server-side
    # grammar and leaks the internal tool call as the answer.
    assert _resolve_format(None, None) == json_schema_format(ANY_OBJECT_SCHEMA)


def test_resolve_format_wraps_bare_schema():
    assert _resolve_format(CITY_SCHEMA, None) == json_schema_format(CITY_SCHEMA)


def test_resolve_format_passes_through_explicit_format():
    fmt = {"type": "json_object"}
    assert _resolve_format(None, fmt) is fmt


def test_resolve_format_rejects_both():
    with pytest.raises(ValidationError, match="not both"):
        _resolve_format(CITY_SCHEMA, {"type": "json_object"})


"""
JSON extraction
"""


def test_extract_plain_json():
    assert _extract_json('{"capital": "Paris"}') == {"capital": "Paris"}


def test_extract_strips_think_block():
    # The RAG grammar permits a think block before the final JSON answer.
    raw = '<think>Sufficient information gathered.</think>\n{"capital": "Paris"}'
    assert _extract_json(raw) == {"capital": "Paris"}


def test_extract_strips_multiline_think_block():
    raw = '<think>line one\nline two</think>{"a": 1}'
    assert _extract_json(raw) == {"a": 1}


def test_extract_strips_markdown_fence():
    assert _extract_json('```json\n{"a": 1}\n```') == {"a": 1}


def test_extract_top_level_array():
    assert _extract_json('[{"city": "NYC"}]') == [{"city": "NYC"}]


def test_extract_falls_back_to_embedded_object():
    assert _extract_json('Here you go: {"a": 1} hope that helps') == {"a": 1}


def test_extract_raises_on_unparseable():
    with pytest.raises(ValidationError, match="could not parse JSON"):
        _extract_json("I could not find an answer.")


"""
Tool call leak
"""


def test_leak_guard_rejects_functioncall():
    leaked = {"name": "functioncall", "arguments": {"name": "dql_v1", "arguments": {}}}
    with pytest.raises(ValidationError, match="internal tool call"):
        _check_tool_call_leak(leaked)


def test_leak_guard_passes_normal_answers():
    answer = {"country": "France", "capital": "Paris"}
    assert _check_tool_call_leak(answer) is answer


def test_leak_guard_allows_name_without_arguments():
    # A legitimate answer may well have a "name" field.
    answer = {"name": "functioncall"}
    assert _check_tool_call_leak(answer) is answer


def test_leak_guard_passes_lists():
    answer = [{"city": "NYC"}]
    assert _check_tool_call_leak(answer) is answer


"""
Streaming error path

ask() opens a streaming response, so reading the error body must happen before
raising -- otherwise httpx raises ResponseNotRead instead of AuthError/RateLimitError.
httpx.MockTransport with content= pre-fills the body, which masks this bug (the body
looks "already read"), so these use a real SyncByteStream/AsyncByteStream that defers
content the way a genuine chunked network response would.
"""


class _SyncSlowStream(httpx.SyncByteStream):
    def __init__(self, chunks):
        self._chunks = chunks

    def __iter__(self):
        for chunk in self._chunks:
            yield chunk

    def close(self):
        pass


class _AsyncSlowStream(httpx.AsyncByteStream):
    def __init__(self, chunks):
        self._chunks = chunks

    async def __aiter__(self):
        for chunk in self._chunks:
            yield chunk

    async def aclose(self):
        pass


def test_ask_streaming_401_raises_auth_error_with_message():
    body = b'{"message": "Unauthorized. Incorrect token.", "requestId": "abc"}'

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(401, stream=_SyncSlowStream([body]))

    db = Diffbot(token="test-token", transport=httpx.MockTransport(handler))
    with pytest.raises(AuthError) as exc_info:
        list(db.ask([{"role": "user", "content": "hi"}]))
    assert exc_info.value.message == "Unauthorized. Incorrect token."
    assert exc_info.value.request_id == "abc"


def test_ask_streaming_429_raises_rate_limit_error_with_retry_after():
    body = b'{"message": "slow down"}'

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(429, headers={"retry-after": "5"}, stream=_SyncSlowStream([body]))

    db = Diffbot(token="test-token", retry=False, transport=httpx.MockTransport(handler))
    with pytest.raises(RateLimitError) as exc_info:
        list(db.ask([{"role": "user", "content": "hi"}]))
    assert exc_info.value.retry_after == "5"
    assert exc_info.value.message == "slow down"


@pytest.mark.anyio
async def test_async_ask_streaming_401_raises_auth_error_with_message():
    body = b'{"message": "Unauthorized. Incorrect token.", "requestId": "abc"}'

    async def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(401, stream=_AsyncSlowStream([body]))

    db = DiffbotAsync(token="test-token", transport=httpx.MockTransport(handler))
    with pytest.raises(AuthError) as exc_info:
        async for _ in db.ask([{"role": "user", "content": "hi"}]):
            pass
    assert exc_info.value.message == "Unauthorized. Incorrect token."
    assert exc_info.value.request_id == "abc"


@pytest.mark.anyio
async def test_async_ask_streaming_429_raises_rate_limit_error_with_retry_after():
    body = b'{"message": "slow down"}'

    async def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(429, headers={"retry-after": "5"}, stream=_AsyncSlowStream([body]))

    db = DiffbotAsync(token="test-token", retry=False, transport=httpx.MockTransport(handler))
    with pytest.raises(RateLimitError) as exc_info:
        async for _ in db.ask([{"role": "user", "content": "hi"}]):
            pass
    assert exc_info.value.retry_after == "5"
    assert exc_info.value.message == "slow down"


"""
Live
"""


@pytest.mark.live
def test_live_ask(db):
    chunks = list(db.ask([{"role": "user", "content": "What is Diffbot?"}]))
    response = "".join(chunks)
    assert len(response) > 0


@pytest.mark.live
def test_live_ask_json_no_schema(db):
    result = db.ask_json([{"role": "user", "content": "What is the capital of France?"}])
    assert isinstance(result, dict)
    assert "paris" in json.dumps(result).lower()


@pytest.mark.live
def test_live_ask_json_no_schema_with_system_message(db):
    # A system message reproducibly triggered the tool-call leak under
    # {"type": "json_object"}; the default format must not regress to it.
    messages = [
        {"role": "system", "content": "Current local time: Friday, August 14, 2026"},
        {"role": "user", "content": "What is the capital of France?"},
    ]
    result = db.ask_json(messages)
    assert "paris" in json.dumps(result).lower()


@pytest.mark.live
def test_live_ask_json_schema(db):
    result = db.ask_json(
        [{"role": "user", "content": "What is the capital of France?"}],
        CITY_SCHEMA,
    )
    assert result["country"].lower() == "france"
    assert result["capital"].lower() == "paris"


@pytest.mark.live
def test_live_ask_streams_with_response_format(db):
    chunks = list(
        db.ask(
            [{"role": "user", "content": "What is the capital of France?"}],
            response_format=json_schema_format(CITY_SCHEMA),
        )
    )
    assert json.loads("".join(chunks))["capital"].lower() == "paris"


@pytest.mark.live
def test_live_ask_json_nested_schema(db):
    schema = {
        "type": "object",
        "properties": {
            "company": {
                "type": "object",
                "properties": {"name": {"type": "string"}, "founded": {"type": "integer"}},
                "required": ["name", "founded"],
            },
            "products": {"type": "array", "items": {"type": "string"}},
        },
        "required": ["company", "products"],
    }
    result = db.ask_json([{"role": "user", "content": "Tell me about Diffbot the company."}], schema)
    assert "diffbot" in result["company"]["name"].lower()
    assert isinstance(result["products"], list)


@pytest.mark.live
@pytest.mark.anyio
async def test_live_ask_json_async(live_token):
    async with DiffbotAsync(token=live_token) as db:
        result = await db.ask_json(
            [{"role": "user", "content": "What is the capital of France?"}],
            CITY_SCHEMA,
        )
    assert result["capital"].lower() == "paris"
