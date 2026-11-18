"""Diffbot web search API."""

from typing import TYPE_CHECKING, Any, Dict, Optional, Sequence, Union, get_args

from ._constants import LLM_BASE
from .errors import ValidationError
from .types import SnippetLength, WebSearchResponse

if TYPE_CHECKING:
    from .client import Diffbot, DiffbotAsync

WEB_SEARCH_BASE = f"{LLM_BASE}/api/v1/web_search"

SNIPPET_LENGTHS = get_args(SnippetLength)
MAX_TEXT_VALUES = 5


def _build_web_search_request(
    client: Any,
    text: Union[str, Sequence[str]],
    num_results: Optional[int],
    max_tokens: Optional[int],
    snippet_length: Optional[SnippetLength],
) -> Any:
    headers = {"Authorization": f"Bearer {client.token}"}
    params: Dict[str, Any] = {}
    if isinstance(text, str):
        params["text"] = text
    else:
        values = list(text)
        if not 1 <= len(values) <= MAX_TEXT_VALUES:
            raise ValidationError(f"text must be a string or 1-{MAX_TEXT_VALUES} strings; got {len(values)}")
        params["text"] = values  # sent as repeated text= params
    if num_results is not None:
        params["size"] = num_results
    if max_tokens is not None:
        params["maxTokens"] = max_tokens
    if snippet_length is not None:
        length = snippet_length.lower() if isinstance(snippet_length, str) else snippet_length
        if length not in SNIPPET_LENGTHS:
            raise ValidationError(
                f"snippet_length must be one of {', '.join(SNIPPET_LENGTHS)}; got {snippet_length!r}"
            )
        params["snippetLength"] = length.upper()
        if params["snippetLength"] == "FULL":
            # the reranker always chunks; only the unranked path returns the stored page
            params["rerank"] = "none"
    return headers, params


def web_search(
    client: "Diffbot",
    text: Union[str, Sequence[str]],
    *,
    num_results: Optional[int] = None,
    max_tokens: Optional[int] = None,
    snippet_length: Optional[SnippetLength] = None,
) -> WebSearchResponse:
    headers, params = _build_web_search_request(client, text, num_results, max_tokens, snippet_length)
    response = client.request("GET", client.web_search_url, headers=headers, params=params)
    return response.json()


async def web_search_async(
    client: "DiffbotAsync",
    text: Union[str, Sequence[str]],
    *,
    num_results: Optional[int] = None,
    max_tokens: Optional[int] = None,
    snippet_length: Optional[SnippetLength] = None,
) -> WebSearchResponse:
    headers, params = _build_web_search_request(client, text, num_results, max_tokens, snippet_length)
    response = await client.request("GET", client.web_search_url, headers=headers, params=params)
    return response.json()
