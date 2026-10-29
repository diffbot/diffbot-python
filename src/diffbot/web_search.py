"""Diffbot web search API."""

from typing import TYPE_CHECKING, Any, Dict, List, Optional

if TYPE_CHECKING:
    from .client import Diffbot, DiffbotAsync

WEB_SEARCH_BASE = "https://llm.diffbot.com/api/v1/web_search"


def web_search(
    client: "Diffbot",
    text: str,
    *,
    num_results: Optional[int] = None,
    max_tokens: Optional[int] = None,
    snippet_length: Optional[str] = None,
) -> Dict[str, Any]:
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
    response = client._http.get(client.web_search_url, headers=headers, params=params)
    client._raise_for_status(response)
    return response.json()


async def web_search_async(
    client: "DiffbotAsync",
    text: str,
    *,
    num_results: Optional[int] = None,
    max_tokens: Optional[int] = None,
    snippet_length: Optional[str] = None,
) -> Dict[str, Any]:
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
    response = await client._http.get(client.web_search_url, headers=headers, params=params)
    client._raise_for_status(response)
    return response.json()
