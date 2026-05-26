"""The Diffbot client classes (sync and async)."""

import pathlib
from types import TracebackType
from typing import Any, AsyncIterator, Dict, Iterator, List, Optional, Sequence, Type, Union

import httpx

from . import __version__
from .errors import APIError, AuthError, RateLimitError, ValidationError
from .extract import extract as _extract, extract_async as _extract_async
from .ask import ask as _ask, ask_async as _ask_async
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
    dql_parallel as _dql_parallel,
    dql_refresh_ontology as _dql_refresh_ontology,
)
from .web_search import (
    WEB_SEARCH_BASE,
    web_search as _web_search,
    web_search_async as _web_search_async,
)
from .nlp import (
    NLP_BASE,
    entities as _entities,
    entities_async as _entities_async,
)

EXTRACT_BASE = "https://api.diffbot.com/v3"
CRAWL_BASE = "https://api.diffbot.com/v3/crawl"
DIFFBOT_LLM_BASE = "https://llm.diffbot.com/rag/v1/chat/completions"
DEFAULT_TIMEOUT = 30.0


class Diffbot:
    """Client for the Diffbot APIs.

    Example:
        >>> from diffbot import Diffbot
        >>> db = Diffbot(token=os.getenv("DIFFBOT_API_TOKEN"))
        >>> db.extract("https://example.com")
    """

    def __init__(
        self,
        token: str,
        *,
        timeout: float = DEFAULT_TIMEOUT,
        analyze_url: str = EXTRACT_BASE,
        llm_url: str = DIFFBOT_LLM_BASE,
        crawler_url: str = CRAWL_BASE,
        web_search_url: str = WEB_SEARCH_BASE,
        nlp_url: str = NLP_BASE,
        transport: Optional[httpx.BaseTransport] = None,
    ):
        if not token:
            raise ValidationError("token is required")
        self.token = token
        self.analyze_url = analyze_url
        self.llm_url = llm_url
        self.crawler_url = crawler_url
        self.web_search_url = web_search_url
        self.nlp_url = nlp_url
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

    def _raise_for_status(self, response: httpx.Response) -> None:
        if response.is_success:
            return
        status = response.status_code
        body = response.text
        if status in (401, 403):
            raise AuthError(status, body)
        if status == 429:
            raise RateLimitError(status, body, retry_after=response.headers.get("retry-after"))
        raise APIError(status, body)

    def extract(self, url: str, api: str = "analyze", fmt: str = "markdown") -> Dict[str, Any]:
        """Extract structured content from a URL. Returns the raw Diffbot API response."""
        return _extract(self, url, api=api, fmt=fmt)

    def ask(self, messages: List[Dict[str, str]]) -> Iterator[str]:
        """Stream a response from the Diffbot LLM RAG API."""
        yield from _ask(self, messages)

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
        format: str = "json",
        filter: Optional[str] = None,
        exportspec: Optional[str] = None,
        extra: Optional[Dict[str, str]] = None,
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

    def web_search(self, text: str, *, num_results: Optional[int] = None, max_tokens: Optional[int] = None) -> Dict[str, Any]:
        """Search the web via the Diffbot LLM web search API."""
        return _web_search(self, text, num_results=num_results, max_tokens=max_tokens)

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
        analyze_url: str = EXTRACT_BASE,
        llm_url: str = DIFFBOT_LLM_BASE,
        crawler_url: str = CRAWL_BASE,
        web_search_url: str = WEB_SEARCH_BASE,
        nlp_url: str = NLP_BASE,
        transport: Optional[httpx.AsyncBaseTransport] = None,
    ):
        if not token:
            raise ValidationError("token is required")
        self.token = token
        self.analyze_url = analyze_url
        self.llm_url = llm_url
        self.crawler_url = crawler_url
        self.web_search_url = web_search_url
        self.nlp_url = nlp_url
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

    def _raise_for_status(self, response: httpx.Response) -> None:
        if response.is_success:
            return
        status = response.status_code
        body = response.text
        if status in (401, 403):
            raise AuthError(status, body)
        if status == 429:
            raise RateLimitError(status, body, retry_after=response.headers.get("retry-after"))
        raise APIError(status, body)

    async def extract(self, url: str, api: str = "analyze", fmt: str = "markdown") -> Dict[str, Any]:
        """Extract structured content from a URL. Returns the raw Diffbot API response."""
        return await _extract_async(self, url, api=api, fmt=fmt)

    async def ask(self, messages: List[Dict[str, str]]) -> AsyncIterator[str]:
        """Stream a response from the Diffbot LLM RAG API."""
        async for chunk in _ask_async(self, messages):
            yield chunk

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
        format: str = "json",
        filter: Optional[str] = None,
        exportspec: Optional[str] = None,
        extra: Optional[Dict[str, str]] = None,
        raw: bool = False,
    ) -> Union[Dict[str, Any], bytes]:
        """Run a DQL query against the Diffbot Knowledge Graph.

        Returns the parsed JSON response, or the raw response bytes when raw=True
        (e.g. to retrieve CSV/export formats undecoded).
        """
        return await _dql_async(self, query, size=size, from_=from_, format=format, filter=filter, exportspec=exportspec, extra=extra, raw=raw)

    async def web_search(self, text: str, *, num_results: Optional[int] = None, max_tokens: Optional[int] = None) -> Dict[str, Any]:
        """Search the web via the Diffbot LLM web search API."""
        return await _web_search_async(self, text, num_results=num_results, max_tokens=max_tokens)

    async def entities(self, text: str, *, lang: str = "auto") -> Dict[str, Any]:
        """Identify and resolve entities and sentiment in text using the Diffbot NLP API.

        Entity IDs can be looked up in the Knowledge Graph via dql() using
        id:or("id1","id2","id3") — no type: declaration required.
        """
        return await _entities_async(self, text, lang=lang)
