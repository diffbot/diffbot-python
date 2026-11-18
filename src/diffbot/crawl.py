"""Diffbot Crawler API: start crawls, manage crawler jobs."""

import asyncio
import csv
import io
import json
import time
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING, Any, AsyncIterator, Dict, Iterator, List, Optional, Sequence, Union

from .errors import APIError, JobError
from .types import CrawlDownloadFormat, CrawlJob

if TYPE_CHECKING:
    from .client import Diffbot, DiffbotAsync


class CrawlEventType(Enum):
    JOB_CREATED = "job_created"
    URL_PROCESSED = "url_processed"


@dataclass
class CrawlEvent:
    """An event yielded while a crawl is in flight."""
    event_type: CrawlEventType
    timestamp: str
    details: Dict[str, Any]


def crawl(
    client: "Diffbot",
    site: str,
    hops: int = 2,
    job_name: Optional[str] = None,
    max_to_crawl: int = 100,
    max_to_process: int = 100,
    restrict_domain: bool = True,
    api_url: str = "",
    crawl_delay: float = -1,
    url_crawl_pattern: Optional[str] = None,
    url_process_pattern: Optional[str] = None,
    obey_robots: bool = False,
    use_proxies: bool = False,
    custom_headers: Optional[Union[str, Sequence[str]]] = None,
    watch: bool = False,
    poll_interval: float = 2.0,
    *,
    url_crawl_regex: Optional[str] = None,
    url_process_regex: Optional[str] = None,
    page_process_pattern: Optional[str] = None,
    max_to_crawl_per_subdomain: Optional[int] = None,
    max_to_process_per_subdomain: Optional[int] = None,
    use_canonical: Optional[bool] = None,
    notify_webhook: Optional[str] = None,
    notify_email: Optional[str] = None,
) -> Iterator[CrawlEvent]:
    """Create a crawler job and yield a JOB_CREATED event. If watch=True, poll until
    completion and yield URL_PROCESSED events for each crawled URL.

    ``job_name`` must be at most 30 characters; the crawler answers an overlong name
    with HTTP 200 + ``errorCode`` 505 and creates nothing, which raises ``APIError``.

    Recommended pattern for tools that can't block on a long crawl: start with
    ``crawl(..., watch=False)``, poll :func:`crawl_get_job` until its
    ``jobStatus.status`` is terminal, then fetch results with :func:`crawl_download`.

    Create options are sent as query params on the existing GET. ``custom_headers`` is
    one ``"Name: value"`` string or a sequence of them (sent as repeated params).
    Recurring-crawl admin (``repeat``, ``maxRounds``, ...) is not exposed."""
    if not site.startswith("http"):
        site = f"https://{site}"
    if not job_name:
        job_name = f"crawl-{int(time.time())}"

    params = _build_crawl_params(
        client, job_name, site, max_to_crawl, max_to_process, hops, restrict_domain,
        api_url, crawl_delay, url_crawl_pattern, url_process_pattern,
        obey_robots, use_proxies, custom_headers,
        _named_create_options(
            url_crawl_regex, url_process_regex, page_process_pattern, max_to_crawl_per_subdomain,
            max_to_process_per_subdomain, use_canonical, notify_webhook, notify_email,
        ),
    )
    _raise_on_create_error(client.request("GET", client.crawler_url, params=params))

    yield CrawlEvent(
        event_type=CrawlEventType.JOB_CREATED,
        timestamp=datetime.now().isoformat(),
        details={"job_name": job_name},
    )

    if not watch:
        return

    seen_urls: set = set()

    while True:
        status_response = client.request(
            "GET",
            client.crawler_url,
            params={"token": client.token, "name": job_name},
        )
        jobs = status_response.json().get("jobs", [])
        if not jobs:
            break
        job_status = jobs[0].get("jobStatus", {})
        status_code = job_status.get("status", 0)

        urls_csv = crawl_download(client, job_name, format="csv", type="urls")
        if urls_csv:
            for event in _parse_url_csv(urls_csv, seen_urls):
                yield event

        if status_code not in (0, 7):
            message = job_status.get("message", "")
            if "fail" in message.lower() or "error" in message.lower():
                raise JobError(job_name, f"Crawler job failed: {message}")
            break

        time.sleep(poll_interval)


def _raise_on_create_error(response: Any) -> None:
    """The crawler reports some create failures (e.g. a job name over 30 chars, errorCode
    505) as HTTP 200 with ``errorCode``/``error`` in the body and creates nothing; surface
    them instead of returning JOB_CREATED. The error keeps the real status, body and
    headers (``APIError.message`` reads the body's ``error`` field)."""
    try:
        data = response.json()
    except ValueError:
        return
    if isinstance(data, dict) and data.get("errorCode"):
        raise APIError(response.status_code, response.text, headers=dict(response.headers))


def _named_create_options(
    url_crawl_regex: Optional[str],
    url_process_regex: Optional[str],
    page_process_pattern: Optional[str],
    max_to_crawl_per_subdomain: Optional[int],
    max_to_process_per_subdomain: Optional[int],
    use_canonical: Optional[bool],
    notify_webhook: Optional[str],
    notify_email: Optional[str],
) -> Dict[str, Any]:
    """Python names -> wire names for the S2 create options; ``None`` means "not set"."""
    return {
        "urlCrawlRegEx": url_crawl_regex,
        "urlProcessRegEx": url_process_regex,
        "pageProcessPattern": page_process_pattern,
        "maxToCrawlPerSubdomain": max_to_crawl_per_subdomain,
        "maxToProcessPerSubdomain": max_to_process_per_subdomain,
        "useCanonical": None if use_canonical is None else int(use_canonical),
        "notifyWebhook": notify_webhook,
        "notifyEmail": notify_email,
    }


def _build_crawl_params(client: Any, job_name: str, site: str, max_to_crawl: int,
                        max_to_process: int, hops: int, restrict_domain: bool,
                        api_url: str, crawl_delay: float, url_crawl_pattern: Optional[str],
                        url_process_pattern: Optional[str], obey_robots: bool,
                        use_proxies: bool, custom_headers: Optional[Union[str, Sequence[str]]],
                        named: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    params: Dict[str, Any] = {
        "token": client.token,
        "name": job_name,
        "seeds": site,
        "maxToCrawl": max_to_crawl,
        "maxToProcess": max_to_process,
        "maxHops": hops,
        "restrictDomain": 1 if restrict_domain else 0,
    }
    if api_url:
        params["apiUrl"] = api_url
    if crawl_delay > 0:
        params["crawlDelay"] = crawl_delay
    if url_crawl_pattern:
        params["urlCrawlPattern"] = url_crawl_pattern
    if url_process_pattern:
        params["urlProcessPattern"] = url_process_pattern
    if obey_robots:
        params["obeyRobots"] = 1
    if use_proxies:
        params["useProxies"] = 1
    if custom_headers:
        # a sequence becomes repeated ``customHeaders=`` params; a lone string stays a plain value
        params["customHeaders"] = custom_headers if isinstance(custom_headers, str) else list(custom_headers)
    if named:
        params.update({k: v for k, v in named.items() if v is not None})
    return params


def _parse_url_csv(text: str, seen_urls: set) -> List[CrawlEvent]:
    events = []
    reader = csv.DictReader(io.StringIO(text))
    for row in reader:
        url = row.get("Url", "").strip('"')
        if url and url not in seen_urls:
            seen_urls.add(url)
            events.append(CrawlEvent(
                event_type=CrawlEventType.URL_PROCESSED,
                timestamp=row.get("Crawled Time", datetime.now().isoformat()),
                details={"url": url, "status": row.get("Crawl Status", "unknown")},
            ))
    return events


async def crawl_async(
    client: "DiffbotAsync",
    site: str,
    hops: int = 2,
    job_name: Optional[str] = None,
    max_to_crawl: int = 100,
    max_to_process: int = 100,
    restrict_domain: bool = True,
    api_url: str = "",
    crawl_delay: float = -1,
    url_crawl_pattern: Optional[str] = None,
    url_process_pattern: Optional[str] = None,
    obey_robots: bool = False,
    use_proxies: bool = False,
    custom_headers: Optional[Union[str, Sequence[str]]] = None,
    watch: bool = False,
    poll_interval: float = 2.0,
    *,
    url_crawl_regex: Optional[str] = None,
    url_process_regex: Optional[str] = None,
    page_process_pattern: Optional[str] = None,
    max_to_crawl_per_subdomain: Optional[int] = None,
    max_to_process_per_subdomain: Optional[int] = None,
    use_canonical: Optional[bool] = None,
    notify_webhook: Optional[str] = None,
    notify_email: Optional[str] = None,
) -> AsyncIterator[CrawlEvent]:
    if not site.startswith("http"):
        site = f"https://{site}"
    if not job_name:
        job_name = f"crawl-{int(time.time())}"

    params = _build_crawl_params(
        client, job_name, site, max_to_crawl, max_to_process, hops, restrict_domain,
        api_url, crawl_delay, url_crawl_pattern, url_process_pattern,
        obey_robots, use_proxies, custom_headers,
        _named_create_options(
            url_crawl_regex, url_process_regex, page_process_pattern, max_to_crawl_per_subdomain,
            max_to_process_per_subdomain, use_canonical, notify_webhook, notify_email,
        ),
    )
    _raise_on_create_error(await client.request("GET", client.crawler_url, params=params))

    yield CrawlEvent(
        event_type=CrawlEventType.JOB_CREATED,
        timestamp=datetime.now().isoformat(),
        details={"job_name": job_name},
    )

    if not watch:
        return

    seen_urls: set = set()

    while True:
        status_response = await client.request(
            "GET",
            client.crawler_url,
            params={"token": client.token, "name": job_name},
        )
        jobs = status_response.json().get("jobs", [])
        if not jobs:
            break
        job_status = jobs[0].get("jobStatus", {})
        status_code = job_status.get("status", 0)

        urls_csv = await crawl_download_async(client, job_name, format="csv", type="urls")
        if urls_csv:
            for event in _parse_url_csv(urls_csv, seen_urls):
                yield event

        if status_code not in (0, 7):
            message = job_status.get("message", "")
            if "fail" in message.lower() or "error" in message.lower():
                raise JobError(job_name, f"Crawler job failed: {message}")
            break

        await asyncio.sleep(poll_interval)


async def crawl_list_jobs_async(client: "DiffbotAsync") -> List[CrawlJob]:
    response = await client.request("GET", client.crawler_url, params={"token": client.token})
    return response.json().get("jobs", [])


async def crawl_get_job_async(client: "DiffbotAsync", job_name: str) -> CrawlJob:
    response = await client.request(
        "GET",
        client.crawler_url,
        params={"token": client.token, "name": job_name},
    )
    jobs = response.json().get("jobs", [])
    return jobs[0] if jobs else {}


async def crawl_delete_job_async(client: "DiffbotAsync", job_name: str) -> None:
    # A GET-shaped mutation: retrying it blindly risks issuing the delete twice.
    await client.request(
        "GET",
        client.crawler_url,
        params={"token": client.token, "name": job_name, "delete": 1},
        retryable=False,
    )


def crawl_list_jobs(client: "Diffbot") -> List[CrawlJob]:
    response = client.request("GET", client.crawler_url, params={"token": client.token})
    return response.json().get("jobs", [])


def crawl_get_job(client: "Diffbot", job_name: str) -> CrawlJob:
    response = client.request(
        "GET",
        client.crawler_url,
        params={"token": client.token, "name": job_name},
    )
    jobs = response.json().get("jobs", [])
    return jobs[0] if jobs else {}


def crawl_delete_job(client: "Diffbot", job_name: str) -> None:
    # A GET-shaped mutation: retrying it blindly risks issuing the delete twice.
    client.request(
        "GET",
        client.crawler_url,
        params={"token": client.token, "name": job_name, "delete": 1},
        retryable=False,
    )


def _download_params(client: Any, name: str, format: CrawlDownloadFormat, type: Optional[str], num: Optional[int]) -> Dict[str, Any]:
    params: Dict[str, Any] = {"token": client.token, "name": name}
    if format == "csv":
        params["format"] = "csv"
    if type is not None:
        params["type"] = type
    if num is not None:
        params["num"] = num
    return params


def _decode_download(name: str, text: str, format: CrawlDownloadFormat, type: Optional[str]) -> Any:
    # The ``urls`` report is always CSV text, whatever ``format`` says.
    if format == "csv" or type == "urls":
        return text
    if not text.strip():
        return []
    data = json.loads(text)
    if not isinstance(data, list):
        # e.g. ``{"errorCode": ..., "error": ...}`` for an unknown job
        error = data.get("error") if isinstance(data, dict) else None
        raise JobError(name, f"Crawl data download failed: {error or 'unexpected response'}")
    return data


# The public, overloaded signatures live on ``Diffbot.crawl_download`` /
# ``DiffbotAsync.crawl_download`` (``format="csv"`` -> ``str``, else records).
def crawl_download(
    client: "Diffbot",
    name: str,
    *,
    format: CrawlDownloadFormat = "json",
    type: Optional[str] = None,
    num: Optional[int] = None,
) -> Any:
    response = client.request(
        "GET",
        f"{client.crawler_url}/data",
        params=_download_params(client, name, format, type, num),
        follow_redirects=True,
    )
    return _decode_download(name, response.text, format, type)


async def crawl_download_async(
    client: "DiffbotAsync",
    name: str,
    *,
    format: CrawlDownloadFormat = "json",
    type: Optional[str] = None,
    num: Optional[int] = None,
) -> Any:
    response = await client.request(
        "GET",
        f"{client.crawler_url}/data",
        params=_download_params(client, name, format, type, num),
        follow_redirects=True,
    )
    return _decode_download(name, response.text, format, type)
