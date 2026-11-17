"""The Diffbot client classes (sync and async)."""

import pathlib
from types import TracebackType
from typing import Any, AsyncIterator, Dict, Iterator, List, Mapping, Optional, Sequence, Type, Union

import httpx

from . import __version__
from ._constants import API_BASE, DEFAULT_TIMEOUT, KG_BASE, LLM_BASE, NLP_HOST_BASE
from ._transport import (
    QueryParams,
    RetryPolicy,
    request as _transport_request,
    request_async as _transport_request_async,
    resolve_retry_policy,
)
from .errors import ValidationError
from .types import ChatMessage, ExportFormat, ResponseFormat, SnippetLength
from .extract import extract as _extract, extract_async as _extract_async
from .ask import (
    ask as _ask,
    ask_async as _ask_async,
    ask_json as _ask_json,
    ask_json_async as _ask_json_async,
)
from .crawl import (
    CrawlEvent,
    crawl as _crawl,
    crawl_async as _crawl_async,
    crawl_delete_job as _crawl_delete_job,
    crawl_delete_job_async as _crawl_delete_job_async,
    crawl_get_job as _crawl_get_job,
    crawl_get_job_async as _crawl_get_job_async,
    crawl_list_jobs as _crawl_list_jobs,
    crawl_list_jobs_async as _crawl_list_jobs_async,
)
from .kg import (
    dql as _dql,
    dql_async as _dql_async,
    dql_fetch_ontology as _dql_fetch_ontology,
    dql_fetch_ontology_async as _dql_fetch_ontology_async,
    dql_parallel as _dql_parallel,
    dql_parallel_async as _dql_parallel_async,
    dql_refresh_ontology as _dql_refresh_ontology,
)
from .ontology import Ontology
from .web_search import (
    web_search as _web_search,
    web_search_async as _web_search_async,
)
from .nlp import (
    entities as _entities,
    entities_async as _entities_async,
)


class Diffbot:
    """Client for the Diffbot APIs.

    Example:
        >>> from diffbot import Diffbot, resolve_token
        >>> db = Diffbot(token=resolve_token())  # env var or ~/.diffbot/credentials
        >>> db.extract("https://example.com")
    """

    def __init__(
        self,
        token: str,
        *,
        timeout: float = DEFAULT_TIMEOUT,
        retry: Union[RetryPolicy, bool, None] = None,
        api_base: str = API_BASE,
        kg_base: str = KG_BASE,
        llm_base: str = LLM_BASE,
        nlp_base: str = NLP_HOST_BASE,
        analyze_url: Optional[str] = None,
        llm_url: Optional[str] = None,
        crawler_url: Optional[str] = None,
        web_search_url: Optional[str] = None,
        nlp_url: Optional[str] = None,
        dql_url: Optional[str] = None,
        ontology_url: Optional[str] = None,
        transport: Optional[httpx.BaseTransport] = None,
    ):
        if not token:
            raise ValidationError("token is required")
        self.token = token
        self.api_base = api_base
        self.kg_base = kg_base
        self.llm_base = llm_base
        self.nlp_base = nlp_base
        # analyze_url/crawler_url are bases the SDK appends to (/{api}, /data); the
        # rest are complete endpoints. Each *_url option wins over its matching base
        # when set, so pointing the whole SDK at a staging host is a one-liner while
        # still allowing a single endpoint to be overridden independently.
        self.analyze_url = analyze_url or f"{api_base}/v3"
        self.crawler_url = crawler_url or f"{api_base}/v3/crawl"
        self.llm_url = llm_url or f"{llm_base}/rag/v1/chat/completions"
        self.web_search_url = web_search_url or f"{llm_base}/api/v1/web_search"
        self.nlp_url = nlp_url or f"{nlp_base}/v1/"
        self.dql_url = dql_url or f"{kg_base}/kg/v3/dql"
        self.ontology_url = ontology_url or f"{kg_base}/kg/ontology"
        self._retry_policy = resolve_retry_policy(retry)
        self._http = httpx.Client(
            timeout=timeout,
            headers={"User-Agent": f"diffbot-python/{__version__}"},
            transport=transport,
        )

    def __enter__(self) -> "Diffbot":
        return self

    def __exit__(
        self,
        exc_type: Optional[Type[BaseException]],
        exc: Optional[BaseException],
        tb: Optional[TracebackType],
    ) -> None:
        self.close()

    def close(self) -> None:
        self._http.close()

    def request(
        self,
        method: str,
        url: str,
        *,
        params: Optional[QueryParams] = None,
        headers: Optional[Dict[str, str]] = None,
        json: Optional[Any] = None,
        content: Optional[Union[str, bytes]] = None,
        data: Optional[Dict[str, Any]] = None,
        timeout: Optional[float] = None,
        retryable: bool = True,
        follow_redirects: Optional[bool] = None,
        stream: bool = False,
    ) -> httpx.Response:
        """Send a request through this client's transport (retry policy, timeout)
        and raise for a non-2xx status. Returns the raw :class:`httpx.Response`.

        With ``stream=True`` the response body is left unread on success — the
        caller must iterate it and call ``.close()``.
        """
        return _transport_request(
            self._http,
            self._retry_policy,
            method,
            url,
            params=params,
            headers=headers,
            json=json,
            content=content,
            data=data,
            timeout=timeout,
            retryable=retryable,
            follow_redirects=follow_redirects,
            stream=stream,
        )

    def extract(self, url: str, api: str = "analyze", fmt: str = "markdown") -> Dict[str, Any]:
        """Extract structured content from a URL. Returns the raw Diffbot API response."""
        return _extract(self, url, api=api, fmt=fmt)

    def ask(
        self,
        messages: List[ChatMessage],
        *,
        response_format: Optional[ResponseFormat] = None,
    ) -> Iterator[str]:
        """Stream a response from the Diffbot LLM RAG API.

        Pass ``response_format`` to constrain the output, e.g.
        ``{"type": "json_object"}`` or ``diffbot.json_schema_format(schema)``.
        """
        yield from _ask(self, messages, response_format=response_format)

    def ask_json(
        self,
        messages: List[ChatMessage],
        schema: Optional[Dict[str, Any]] = None,
        *,
        response_format: Optional[ResponseFormat] = None,
    ) -> Any:
        """Ask the Diffbot LLM and return the answer parsed as JSON.

        With ``schema`` (a JSON Schema dict) the model is constrained to it by
        grammar; without one it falls back to unconstrained JSON output.
        """
        return _ask_json(self, messages, schema, response_format=response_format)

    def crawl(self, site: str, **kwargs: Any) -> Iterator[CrawlEvent]:
        """Start a crawl job."""
        yield from _crawl(self, site, **kwargs)

    def crawl_list_jobs(self) -> List[Dict[str, Any]]:
        """List all crawler jobs for this token."""
        return _crawl_list_jobs(self)

    def crawl_get_job(self, job_name: str) -> Dict[str, Any]:
        """Get the status of a crawler job."""
        return _crawl_get_job(self, job_name)

    def crawl_delete_job(self, job_name: str) -> None:
        """Delete a crawler job."""
        _crawl_delete_job(self, job_name)

    def dql(
        self,
        query: str,
        *,
        size: int = 10,
        from_: int = 0,
        format: ExportFormat = "json",
        filter: Optional[str] = None,
        exportspec: Optional[str] = None,
        extra: Optional[Mapping[str, Any]] = None,
        raw: bool = False,
    ) -> Union[Dict[str, Any], bytes]:
        """Run a DQL query against the Diffbot Knowledge Graph.

        Returns the parsed JSON response, or the raw response bytes when raw=True
        (e.g. to retrieve CSV/export formats undecoded).
        """
        return _dql(self, query, size=size, from_=from_, format=format, filter=filter, exportspec=exportspec, extra=extra, raw=raw)

    def dql_parallel(self, queries: Sequence[Dict[str, Any]], *, workers: int = 8) -> List[Union[Dict[str, Any], bytes]]:
        """Run multiple DQL queries concurrently. Each item is a dict of dql() keyword args."""
        return _dql_parallel(self, queries, workers=workers)

    def dql_refresh_ontology(self, dest: pathlib.Path) -> None:
        """Download the Diffbot Knowledge Graph ontology and write it to dest."""
        _dql_refresh_ontology(self, dest)

    def dql_fetch_ontology(self) -> Ontology:
        """Download the ontology and return it as a queryable Ontology (no caching)."""
        return _dql_fetch_ontology(self)

    def web_search(
        self,
        text: str,
        *,
        num_results: Optional[int] = None,
        max_tokens: Optional[int] = None,
        snippet_length: Optional[SnippetLength] = None,
    ) -> Dict[str, Any]:
        """Search the web via the Diffbot LLM web search API.

        snippet_length: "short", "medium", "long" or "full" — how much of each
        page's matching content to return. Omit for the API default (long).
        "full" returns the whole stored page (reranking is disabled for it);
        use it with a url:<URL> query.
        """
        return _web_search(self, text, num_results=num_results, max_tokens=max_tokens, snippet_length=snippet_length)

    def entities(self, text: str, *, lang: str = "auto") -> Dict[str, Any]:
        """Identify and resolve entities and sentiment in text using the Diffbot NLP API.

        Entity IDs can be looked up in the Knowledge Graph via dql() using
        id:or("id1","id2","id3") — no type: declaration required.
        """
        return _entities(self, text, lang=lang)


class DiffbotAsync:
    """Async client for Diffbot APIs.

    Example:
        >>> async with DiffbotAsync(token=os.getenv("DIFFBOT_API_TOKEN")) as db:
        ...     result = await db.extract("https://example.com")
    """

    def __init__(
        self,
        token: str,
        *,
        timeout: float = DEFAULT_TIMEOUT,
        retry: Union[RetryPolicy, bool, None] = None,
        api_base: str = API_BASE,
        kg_base: str = KG_BASE,
        llm_base: str = LLM_BASE,
        nlp_base: str = NLP_HOST_BASE,
        analyze_url: Optional[str] = None,
        llm_url: Optional[str] = None,
        crawler_url: Optional[str] = None,
        web_search_url: Optional[str] = None,
        nlp_url: Optional[str] = None,
        dql_url: Optional[str] = None,
        ontology_url: Optional[str] = None,
        transport: Optional[httpx.AsyncBaseTransport] = None,
    ):
        if not token:
            raise ValidationError("token is required")
        self.token = token
        self.api_base = api_base
        self.kg_base = kg_base
        self.llm_base = llm_base
        self.nlp_base = nlp_base
        self.analyze_url = analyze_url or f"{api_base}/v3"
        self.crawler_url = crawler_url or f"{api_base}/v3/crawl"
        self.llm_url = llm_url or f"{llm_base}/rag/v1/chat/completions"
        self.web_search_url = web_search_url or f"{llm_base}/api/v1/web_search"
        self.nlp_url = nlp_url or f"{nlp_base}/v1/"
        self.dql_url = dql_url or f"{kg_base}/kg/v3/dql"
        self.ontology_url = ontology_url or f"{kg_base}/kg/ontology"
        self._retry_policy = resolve_retry_policy(retry)
        self._http = httpx.AsyncClient(
            timeout=timeout,
            headers={"User-Agent": f"diffbot-python/{__version__}"},
            transport=transport,
        )

    async def __aenter__(self) -> "DiffbotAsync":
        return self

    async def __aexit__(
        self,
        exc_type: Optional[Type[BaseException]],
        exc: Optional[BaseException],
        tb: Optional[TracebackType],
    ) -> None:
        await self.close()

    async def close(self) -> None:
        await self._http.aclose()

    async def request(
        self,
        method: str,
        url: str,
        *,
        params: Optional[QueryParams] = None,
        headers: Optional[Dict[str, str]] = None,
        json: Optional[Any] = None,
        content: Optional[Union[str, bytes]] = None,
        data: Optional[Dict[str, Any]] = None,
        timeout: Optional[float] = None,
        retryable: bool = True,
        follow_redirects: Optional[bool] = None,
        stream: bool = False,
    ) -> httpx.Response:
        """Async twin of :meth:`Diffbot.request`."""
        return await _transport_request_async(
            self._http,
            self._retry_policy,
            method,
            url,
            params=params,
            headers=headers,
            json=json,
            content=content,
            data=data,
            timeout=timeout,
            retryable=retryable,
            follow_redirects=follow_redirects,
            stream=stream,
        )

    async def extract(self, url: str, api: str = "analyze", fmt: str = "markdown") -> Dict[str, Any]:
        """Extract structured content from a URL. Returns the raw Diffbot API response."""
        return await _extract_async(self, url, api=api, fmt=fmt)

    async def ask(
        self,
        messages: List[ChatMessage],
        *,
        response_format: Optional[ResponseFormat] = None,
    ) -> AsyncIterator[str]:
        """Stream a response from the Diffbot LLM RAG API.

        Pass ``response_format`` to constrain the output, e.g.
        ``{"type": "json_object"}`` or ``diffbot.json_schema_format(schema)``.
        """
        async for chunk in _ask_async(self, messages, response_format=response_format):
            yield chunk

    async def ask_json(
        self,
        messages: List[ChatMessage],
        schema: Optional[Dict[str, Any]] = None,
        *,
        response_format: Optional[ResponseFormat] = None,
    ) -> Any:
        """Ask the Diffbot LLM and return the answer parsed as JSON.

        With ``schema`` (a JSON Schema dict) the model is constrained to it by
        grammar; without one it falls back to unconstrained JSON output.
        """
        return await _ask_json_async(self, messages, schema, response_format=response_format)

    async def crawl(self, site: str, **kwargs: Any) -> AsyncIterator[CrawlEvent]:
        """Start a crawl job. Pass watch=True to poll until completion and yield URL_PROCESSED events."""
        async for event in _crawl_async(self, site, **kwargs):
            yield event

    async def crawl_list_jobs(self) -> List[Dict[str, Any]]:
        """List all crawler jobs for this token."""
        return await _crawl_list_jobs_async(self)

    async def crawl_get_job(self, job_name: str) -> Dict[str, Any]:
        """Get the status of a crawler job."""
        return await _crawl_get_job_async(self, job_name)

    async def crawl_delete_job(self, job_name: str) -> None:
        """Delete a crawler job."""
        await _crawl_delete_job_async(self, job_name)

    async def dql(
        self,
        query: str,
        *,
        size: int = 10,
        from_: int = 0,
        format: ExportFormat = "json",
        filter: Optional[str] = None,
        exportspec: Optional[str] = None,
        extra: Optional[Mapping[str, Any]] = None,
        raw: bool = False,
    ) -> Union[Dict[str, Any], bytes]:
        """Run a DQL query against the Diffbot Knowledge Graph.

        Returns the parsed JSON response, or the raw response bytes when raw=True
        (e.g. to retrieve CSV/export formats undecoded).
        """
        return await _dql_async(self, query, size=size, from_=from_, format=format, filter=filter, exportspec=exportspec, extra=extra, raw=raw)

    async def dql_parallel(self, queries: Sequence[Dict[str, Any]], *, workers: int = 8) -> List[Union[Dict[str, Any], bytes]]:
        """Run multiple DQL queries concurrently. Each item is a dict of dql() keyword args."""
        return await _dql_parallel_async(self, queries, workers=workers)

    async def dql_fetch_ontology(self) -> Ontology:
        """Download the ontology and return it as a queryable Ontology (no caching)."""
        return await _dql_fetch_ontology_async(self)

    async def web_search(
        self,
        text: str,
        *,
        num_results: Optional[int] = None,
        max_tokens: Optional[int] = None,
        snippet_length: Optional[SnippetLength] = None,
    ) -> Dict[str, Any]:
        """Search the web via the Diffbot LLM web search API.

        snippet_length: "short", "medium", "long" or "full" — how much of each
        page's matching content to return. Omit for the API default (long).
        "full" returns the whole stored page (reranking is disabled for it);
        use it with a url:<URL> query.
        """
        return await _web_search_async(self, text, num_results=num_results, max_tokens=max_tokens, snippet_length=snippet_length)

    async def entities(self, text: str, *, lang: str = "auto") -> Dict[str, Any]:
        """Identify and resolve entities and sentiment in text using the Diffbot NLP API.

        Entity IDs can be looked up in the Knowledge Graph via dql() using
        id:or("id1","id2","id3") — no type: declaration required.
        """
        return await _entities_async(self, text, lang=lang)
