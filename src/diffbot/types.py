"""Additive type aliases for existing SDK surfaces.

These are structural overlays over the plain ``dict``/``str`` values the SDK already
accepts and returns — no parsing or validation changes at runtime. ``TypedDict``
members are ``total=False`` where the wire shape genuinely allows a field to be
absent, so a server response missing a field never breaks a type-checked caller.
"""

from typing import Any, Dict, Literal, TypedDict


#: Roles accepted by the Diffbot LLM RAG endpoint's chat messages.
ChatRole = Literal["system", "user", "assistant"]


class ChatMessage(TypedDict):
    role: ChatRole
    content: str


#: `response_format` types accepted by :func:`diffbot.ask.ask`/`ask_json`.
ResponseFormatType = Literal["text", "json_object", "json_schema"]


class JsonSchemaSpec(TypedDict, total=False):
    name: str
    schema: Dict[str, Any]


class ResponseFormat(TypedDict, total=False):
    type: ResponseFormatType
    json_schema: JsonSchemaSpec


#: DQL / Enhance-bulk export formats.
ExportFormat = Literal["json", "jsonl", "csv", "xls", "xlsx"]

#: How much of each page's matching content `web_search` returns.
SnippetLength = Literal["short", "medium", "long", "full"]

#: Documented crawl/bulk job status codes (``docs__crawl__manage.md``):
#: 0 initializing, 6 paused, 7 in progress, 8 admin-paused, 9 complete.
CrawlJobStatusCode = Literal[0, 6, 7, 8, 9]
