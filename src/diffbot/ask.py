"""Diffbot LLM RAG API: stream a chat completion."""

import json
import re
from typing import TYPE_CHECKING, Any, AsyncIterator, Dict, Iterator, List, Optional

from .errors import ValidationError

if TYPE_CHECKING:
    from .client import Diffbot, DiffbotAsync

MODEL = "diffbot-small-xl"

#: `response_format` types accepted by the Diffbot LLM endpoint.
RESPONSE_FORMAT_TYPES = ("text", "json_object", "json_schema")

# The RAG loop may prefix its final answer with a think block, and the model
# occasionally wraps JSON in a markdown fence despite being told not to.
_THINK_BLOCK = re.compile(r"<think>.*?</think>", re.DOTALL)
_JSON_FENCE = re.compile(r"^```(?:json)?\s*|\s*```$", re.MULTILINE)


def json_schema_format(schema: Dict[str, Any], *, name: str = "response") -> Dict[str, Any]:
    """Build a ``response_format`` value that constrains output to ``schema``.

    The endpoint requires the schema nested under ``json_schema.schema``; passing
    it anywhere else is ignored server-side without an error, so prefer this
    helper over hand-building the dict.

    Example:
        >>> json_schema_format({"type": "object", "properties": {"city": {"type": "string"}}})
        {'type': 'json_schema', 'json_schema': {'name': 'response', 'schema': {...}}}
    """
    if not isinstance(schema, dict):
        raise ValidationError("schema must be a JSON Schema dict")
    return {"type": "json_schema", "json_schema": {"name": name, "schema": schema}}


def _validate_response_format(response_format: Optional[Dict[str, Any]]) -> None:
    """Reject shapes the endpoint would accept but silently not enforce."""
    if response_format is None:
        return
    if not isinstance(response_format, dict):
        raise ValidationError("response_format must be a dict")

    fmt_type = response_format.get("type", "text")
    if fmt_type not in RESPONSE_FORMAT_TYPES:
        raise ValidationError(
            f"response_format type must be one of {', '.join(RESPONSE_FORMAT_TYPES)}; got {fmt_type!r}"
        )

    if fmt_type == "json_schema":
        json_schema = response_format.get("json_schema")
        if not isinstance(json_schema, dict) or "schema" not in json_schema:
            raise ValidationError(
                'response_format {"type": "json_schema"} requires the schema nested as '
                '{"json_schema": {"schema": {...}}}. Without it the server returns 200 and '
                "ignores the constraint. Use diffbot.json_schema_format(schema) to build it."
            )


def _build_payload(
    client: Any,
    messages: List[Dict[str, str]],
    *,
    response_format: Optional[Dict[str, Any]] = None,
) -> tuple:
    _validate_response_format(response_format)
    headers = {"Authorization": f"Bearer {client.token}"}
    payload: Dict[str, Any] = {"model": MODEL, "messages": messages, "stream": True}
    if response_format is not None:
        payload["response_format"] = response_format
    return headers, payload


def _parse_chunk(line: str):
    try:
        chunk = json.loads(line.replace("data: ", ""))
    except json.JSONDecodeError:
        return None
    choices = chunk.get("choices")
    if choices and choices[0].get("delta", {}).get("content"):
        return choices[0]["delta"]["content"]
    return None


def _extract_json(text: str) -> Any:
    """Parse the model's final answer as JSON, tolerating think blocks and fences."""
    cleaned = _THINK_BLOCK.sub("", text).strip()
    cleaned = _JSON_FENCE.sub("", cleaned).strip()

    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        pass

    # Fall back to the outermost object or array span in the response.
    spans = []
    for opener, closer in (("{", "}"), ("[", "]")):
        start, end = cleaned.find(opener), cleaned.rfind(closer)
        if start != -1 and end > start:
            spans.append((start, cleaned[start : end + 1]))
    for _, span in sorted(spans):
        try:
            return json.loads(span)
        except json.JSONDecodeError:
            continue

    raise ValidationError(f"could not parse JSON from the model response: {text[:200]!r}")


#: Schema used when the caller wants JSON but has no shape in mind. This goes
#: through the json_schema path rather than {"type": "json_object"} on purpose:
#: json_object applies no server-side grammar, so the RAG loop's internal
#: <functioncall> JSON satisfies it and gets returned as the final answer. That
#: is reproducible whenever the request carries a system message.
ANY_OBJECT_SCHEMA = {"type": "object"}


def _resolve_format(
    schema: Optional[Dict[str, Any]],
    response_format: Optional[Dict[str, Any]],
) -> Dict[str, Any]:
    if schema is not None and response_format is not None:
        raise ValidationError("pass either schema or response_format, not both")
    if response_format is not None:
        return response_format
    return json_schema_format(schema if schema is not None else ANY_OBJECT_SCHEMA)


def _check_tool_call_leak(parsed: Any) -> Any:
    """Catch the internal tool call surfacing as the answer (see ANY_OBJECT_SCHEMA)."""
    if isinstance(parsed, dict) and parsed.get("name") == "functioncall" and "arguments" in parsed:
        raise ValidationError(
            "the model returned its internal tool call instead of an answer; this happens with "
            'response_format {"type": "json_object"} because the server applies no grammar to it. '
            "Pass a schema instead."
        )
    return parsed


def ask(
    client: "Diffbot",
    messages: List[Dict[str, str]],
    *,
    response_format: Optional[Dict[str, Any]] = None,
) -> Iterator[str]:
    headers, payload = _build_payload(client, messages, response_format=response_format)
    with client._http.stream("POST", client.llm_url, headers=headers, json=payload) as response:
        client._raise_for_status(response)
        for line in response.iter_lines():
            if line:
                content = _parse_chunk(line)
                if content:
                    yield content


async def ask_async(
    client: "DiffbotAsync",
    messages: List[Dict[str, str]],
    *,
    response_format: Optional[Dict[str, Any]] = None,
) -> AsyncIterator[str]:
    headers, payload = _build_payload(client, messages, response_format=response_format)
    async with client._http.stream("POST", client.llm_url, headers=headers, json=payload) as response:
        client._raise_for_status(response)
        async for line in response.aiter_lines():
            if line:
                content = _parse_chunk(line)
                if content:
                    yield content


def ask_json(
    client: "Diffbot",
    messages: List[Dict[str, str]],
    schema: Optional[Dict[str, Any]] = None,
    *,
    response_format: Optional[Dict[str, Any]] = None,
) -> Any:
    fmt = _resolve_format(schema, response_format)
    text = "".join(ask(client, messages, response_format=fmt))
    return _check_tool_call_leak(_extract_json(text))


async def ask_json_async(
    client: "DiffbotAsync",
    messages: List[Dict[str, str]],
    schema: Optional[Dict[str, Any]] = None,
    *,
    response_format: Optional[Dict[str, Any]] = None,
) -> Any:
    fmt = _resolve_format(schema, response_format)
    chunks = [chunk async for chunk in ask_async(client, messages, response_format=fmt)]
    return _check_tool_call_leak(_extract_json("".join(chunks)))
