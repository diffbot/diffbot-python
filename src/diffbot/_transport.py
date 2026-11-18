"""Shared request-shaping and response-handling helpers for the sync and async clients.

Both ``Diffbot`` and ``DiffbotAsync`` delegate here so the two don't carry duplicate
copies of retry/timeout/error-raising logic; the only difference between them is
whether the underlying ``httpx.Client``/``httpx.AsyncClient`` call is awaited.
"""

import asyncio
import math
import random
import time
from dataclasses import dataclass
from email.utils import parsedate_to_datetime
from typing import Any, Dict, Optional, Sequence, Union

import httpx

from .errors import APIError, AuthError, NotFoundError, RateLimitError

QueryParamValue = Union[str, int, float, bool]
QueryParams = Dict[str, Union[QueryParamValue, Sequence[QueryParamValue], None]]


@dataclass
class RetryPolicy:
    """Retry policy for transient failures (429, 5xx, connection errors).

    ``max_attempts`` counts the initial try, so ``3`` means up to 2 retries. Disable
    per client with ``retry=False`` on the client constructor; disable per call with
    ``retryable=False`` — required for GET-shaped mutations (e.g. ``crawl?delete=1``)
    that must never be retried blindly.

    ``max_delay`` (seconds) caps the exponential backoff and is also the ceiling for
    a server's ``Retry-After``: if a 429/5xx asks for a longer wait (seconds or
    HTTP-date form), the SDK does not sleep or retry and raises at once —
    ``RateLimitError`` with ``retry_after`` set, or ``APIError`` (header in
    ``headers``) for a 5xx.
    """

    max_attempts: int = 3
    base_delay: float = 0.25
    max_delay: float = 5.0
    jitter: bool = True


DEFAULT_RETRY_POLICY = RetryPolicy()


def resolve_retry_policy(retry: Union[RetryPolicy, bool, None]) -> Optional[RetryPolicy]:
    """``None``/``True`` -> default policy (retries on by default); ``False`` -> disabled."""
    if retry is False:
        return None
    if retry is None or retry is True:
        return DEFAULT_RETRY_POLICY
    return retry


def _is_retryable_status(status_code: int) -> bool:
    return status_code == 429 or status_code >= 500


def _parse_retry_after(retry_after: Optional[str]) -> Optional[float]:
    """Parses ``Retry-After`` as seconds or an HTTP date into a non-negative delay (seconds)."""
    if not retry_after:
        return None
    try:
        seconds = float(retry_after)
    except ValueError:
        pass
    else:
        if math.isfinite(seconds):
            return max(0.0, seconds)
        return None
    try:
        dt = parsedate_to_datetime(retry_after)
        return max(0.0, dt.timestamp() - time.time())
    except (TypeError, ValueError):
        return None


def _compute_delay(attempt: int, retry_after: Optional[str], policy: RetryPolicy) -> Optional[float]:
    """Delay before the next attempt: a parseable ``Retry-After`` is honored as given,
    otherwise exponential backoff capped at ``max_delay``. Returns ``None`` when
    ``Retry-After`` exceeds ``max_delay``, meaning "do not retry; raise now"."""
    retry_after_s = _parse_retry_after(retry_after)
    if retry_after_s is not None:
        return None if retry_after_s > policy.max_delay else retry_after_s
    return _backoff_delay(attempt, policy)


def _backoff_delay(attempt: int, policy: RetryPolicy) -> float:
    exponential = min(policy.max_delay, policy.base_delay * (2 ** (attempt - 1)))
    return exponential * (0.5 + random.random() * 0.5) if policy.jitter else exponential


def _retry_delay(
    policy: Optional[RetryPolicy], attempt: int, max_attempts: int, response: httpx.Response
) -> Optional[float]:
    """Seconds to sleep before retrying ``response``, or ``None`` to stop and raise.

    ``None`` also covers a ``Retry-After`` beyond ``policy.max_delay``: the response is
    then raised as-is (``RateLimitError.retry_after`` / ``APIError.headers``) instead of
    sleeping for however long the server asked.
    """
    if not policy or attempt >= max_attempts or not _is_retryable_status(response.status_code):
        return None
    return _compute_delay(attempt, response.headers.get("retry-after"), policy)


def raise_for_status(response: httpx.Response) -> None:
    if response.is_success:
        return
    status = response.status_code
    body = response.text
    headers = dict(response.headers)
    if status in (401, 403):
        raise AuthError(status, body, headers=headers)
    if status == 404:
        raise NotFoundError(status, body, headers=headers)
    if status == 429:
        raise RateLimitError(status, body, retry_after=response.headers.get("retry-after"), headers=headers)
    raise APIError(status, body, headers=headers)


def _build_kwargs(
    params: Optional[QueryParams],
    headers: Optional[Dict[str, str]],
    json: Optional[Any],
    content: Optional[Union[str, bytes]],
    data: Optional[Dict[str, Any]],
    timeout: Optional[float],
) -> Dict[str, Any]:
    kwargs: Dict[str, Any] = {}
    if params is not None:
        kwargs["params"] = params
    if headers is not None:
        kwargs["headers"] = headers
    if json is not None:
        kwargs["json"] = json
    if content is not None:
        kwargs["content"] = content
    if data is not None:
        kwargs["data"] = data
    if timeout is not None:
        kwargs["timeout"] = timeout
    return kwargs


def request(
    http: httpx.Client,
    retry_policy: Optional[RetryPolicy],
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
    """Send a request, retrying on 429/5xx/connection errors per ``retry_policy``, then
    raise for a non-2xx status. The request is rebuilt fresh on each attempt so a
    request body is never resent from an already-consumed stream.

    With ``stream=True`` the response body is left unread on success (the caller
    must iterate it and call ``.close()``), but is still read before raising on a
    non-2xx status — without that, accessing the error body (e.g. via
    ``RateLimitError.message``) would raise ``httpx.ResponseNotRead``.
    """
    kwargs = _build_kwargs(params, headers, json, content, data, timeout)
    send_kwargs: Dict[str, Any] = {} if follow_redirects is None else {"follow_redirects": follow_redirects}
    if stream:
        send_kwargs["stream"] = True
    policy = retry_policy if retryable else None
    max_attempts = policy.max_attempts if policy else 1
    attempt = 1
    while True:
        req = http.build_request(method, url, **kwargs)
        try:
            response = http.send(req, **send_kwargs)
        except httpx.TransportError:
            if policy and attempt < max_attempts:
                time.sleep(_backoff_delay(attempt, policy))
                attempt += 1
                continue
            raise
        delay = _retry_delay(policy, attempt, max_attempts, response)
        if delay is not None:
            if stream:
                response.close()
            time.sleep(delay)
            attempt += 1
            continue
        if response.is_success:
            return response
        response.read()
        raise_for_status(response)


async def request_async(
    http: httpx.AsyncClient,
    retry_policy: Optional[RetryPolicy],
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
    """Async twin of :func:`request`."""
    kwargs = _build_kwargs(params, headers, json, content, data, timeout)
    send_kwargs: Dict[str, Any] = {} if follow_redirects is None else {"follow_redirects": follow_redirects}
    if stream:
        send_kwargs["stream"] = True
    policy = retry_policy if retryable else None
    max_attempts = policy.max_attempts if policy else 1
    attempt = 1
    while True:
        req = http.build_request(method, url, **kwargs)
        try:
            response = await http.send(req, **send_kwargs)
        except httpx.TransportError:
            if policy and attempt < max_attempts:
                await asyncio.sleep(_backoff_delay(attempt, policy))
                attempt += 1
                continue
            raise
        delay = _retry_delay(policy, attempt, max_attempts, response)
        if delay is not None:
            if stream:
                await response.aclose()
            await asyncio.sleep(delay)
            attempt += 1
            continue
        if response.is_success:
            return response
        await response.aread()
        raise_for_status(response)
