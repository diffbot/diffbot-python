"""Diffbot web search API."""

from typing import TYPE_CHECKING, Any, Dict, Optional

from ._constants import LLM_BASE
from .types import SnippetLength, WebSearchResponse

if TYPE_CHECKING:
    from .client import Diffbot, DiffbotAsync

WEB_SEARCH_BASE = f"{LLM_BASE}/api/v1/web_search"


def _build_web_search_request(
    client: Any,
    text: str,
    num_results: Optional[int],
    max_tokens: Optional[int],
    snippet_length: Optional[SnippetLength],
) -> Any:
    headers = {"Authorization": f"Bearer {client.token}"}
    params: Dict[str, Any] = {"text": text}
    if num_results is not None:
        params["size"] = num_results
    if max_tokens is not None:
        params["maxTokens"] = max_tokens
    if snippet_length is not None:
        params["snippetLength"] = snippet_length.upper()
        if params["snippetLength"] == "FULL":
            # the reranker always chunks; only the unranked path returns the stored page
            params["rerank"] = "none"
    return headers, params


def web_search(
    client: "Diffbot",
    text: str,
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
    text: str,
    *,
    num_results: Optional[int] = None,
    max_tokens: Optional[int] = None,
    snippet_length: Optional[SnippetLength] = None,
) -> WebSearchResponse:
    headers, params = _build_web_search_request(client, text, num_results, max_tokens, snippet_length)
    response = await client.request("GET", client.web_search_url, headers=headers, params=params)
    return response.json()
