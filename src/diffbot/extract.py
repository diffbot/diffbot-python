"""Diffbot Analyze API: extract structured content from a URL."""

from typing import TYPE_CHECKING, Any, Dict, Mapping, Optional

if TYPE_CHECKING:
    from .client import Diffbot, DiffbotAsync

from .errors import ExtractionError, ValidationError

#: Keyword options -> wire parameter names. ``fields``/``natural_language`` take a
#: sequence and are comma-joined; everything else is sent as-is.
_OPTION_WIRE: Dict[str, str] = {
    "timeout": "timeout",
    "mode": "mode",
    "fields": "fields",
    "fallback": "fallback",
    "discussion": "discussion",
    "paging": "paging",
    "max_pages": "maxPages",
    "natural_language": "naturalLanguage",
    "summary_num_sentences": "summaryNumSentences",
    "max_tags": "maxTags",
    "tag_confidence": "tagConfidence",
    "category_confidence": "categoryConfidence",
    "use_proxy": "useProxy",
}
_COMMA_JOINED = ("fields", "natural_language")
#: Wire names a caller may not smuggle in through ``extra`` (named options win).
_RESERVED_WIRE = {"token", "url"} | set(_OPTION_WIRE.values())

#: The server-side fetch timeout (ms) when the caller doesn't set one.
DEFAULT_EXTRACT_TIMEOUT_MS = 30000
#: Headroom the transport timeout keeps over the server-side one so the client
#: doesn't abort before the server has a chance to answer.
TRANSPORT_TIMEOUT_MARGIN_S = 10.0


def _build_params(client: Any, url: str, fmt: str, options: Mapping[str, Any]) -> Dict[str, Any]:
    unknown = sorted(set(options) - set(_OPTION_WIRE) - {"extra"})
    if unknown:
        raise TypeError(f"extract() got unexpected keyword argument(s): {', '.join(unknown)}")
    params: Dict[str, Any] = {"token": client.token, "url": url, "timeout": DEFAULT_EXTRACT_TIMEOUT_MS}
    # An explicit ``mode`` overrides the markdown -> llm mapping.
    if fmt == "markdown":
        params["mode"] = "llm"
    for name, value in options.items():
        if name == "extra" or value is None:
            continue
        if name in _COMMA_JOINED and not isinstance(value, str):
            value = ",".join(value)
        params[_OPTION_WIRE[name]] = value
    extra = options.get("extra")
    if extra:
        clash = sorted(_RESERVED_WIRE & set(extra))
        if clash:
            raise ValidationError(
                f"extra may not set {', '.join(clash)}: use the named option instead (token/url are set by the SDK)"
            )
        params.update(extra)
    return params


def _transport_timeout(client: Any, options: Mapping[str, Any]) -> Optional[float]:
    """Per-call transport timeout (seconds), or ``None`` to keep the client's.

    Only raised, never lowered: a caller-set server-side ``timeout`` (ms) needs the
    transport to wait at least that long plus a margin. A client configured with no
    read timeout is left alone.
    """
    timeout_ms = options.get("timeout")
    if timeout_ms is None:
        return None
    client_read = client._http.timeout.read
    needed = timeout_ms / 1000 + TRANSPORT_TIMEOUT_MARGIN_S
    if client_read is not None and needed > client_read:
        return needed
    return None


def _parse_response(client: Any, data: Dict[str, Any]) -> Dict[str, Any]:
    if "errorCode" in data:
        raise ExtractionError(data["errorCode"], data.get("error", ""))
    return data


def _normalize_url(url: str) -> str:
    return url if url.startswith("http") else f"https://{url}"


# The public, per-API overloaded signatures live on ``Diffbot.extract`` /
# ``DiffbotAsync.extract``; these shared implementations return ``Any``.
def extract(client: "Diffbot", url: str, api: str = "analyze", fmt: str = "markdown", **options: Any) -> Any:
    url = _normalize_url(url)
    response = client.request(
        "GET",
        f"{client.analyze_url}/{api}",
        params=_build_params(client, url, fmt, options),
        timeout=_transport_timeout(client, options),
    )
    return _parse_response(client, response.json())


async def extract_async(
    client: "DiffbotAsync", url: str, api: str = "analyze", fmt: str = "markdown", **options: Any
) -> Any:
    url = _normalize_url(url)
    response = await client.request(
        "GET",
        f"{client.analyze_url}/{api}",
        params=_build_params(client, url, fmt, options),
        timeout=_transport_timeout(client, options),
    )
    return _parse_response(client, response.json())
