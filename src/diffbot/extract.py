"""Diffbot Analyze API: extract structured content from a URL."""

from typing import TYPE_CHECKING, Any, Dict

if TYPE_CHECKING:
    from .client import Diffbot, DiffbotAsync

from .errors import ExtractionError


def _build_params(client: Any, url: str, fmt: str) -> Dict[str, Any]:
    params = {"token": client.token, "url": url, "timeout": 30000}
    if fmt == "markdown":
        params["mode"] = "llm"
    return params


def _parse_response(client: Any, data: Dict[str, Any]) -> Dict[str, Any]:
    if "errorCode" in data:
        raise ExtractionError(data["errorCode"], data.get("error", ""))
    return data


def _normalize_url(url: str) -> str:
    return url if url.startswith("http") else f"https://{url}"


def extract(client: "Diffbot", url: str, api: str = "analyze", fmt: str = "markdown") -> Dict[str, Any]:
    url = _normalize_url(url)
    response = client._http.get(
        f"{client.analyze_url}/{api}",
        params=_build_params(client, url, fmt),
    )
    client._raise_for_status(response)
    return _parse_response(client, response.json())


async def extract_async(client: "DiffbotAsync", url: str, api: str = "analyze", fmt: str = "markdown") -> Dict[str, Any]:
    url = _normalize_url(url)
    response = await client._http.get(
        f"{client.analyze_url}/{api}",
        params=_build_params(client, url, fmt),
    )
    client._raise_for_status(response)
    return _parse_response(client, response.json())
