# Changelog

## 3.2.0 (unreleased)

Shared transport foundation, a sync/async de-duplication refactor, and DQL sent
as a POST. The package version in `pyproject.toml` is bumped at release time.

### Changed

- **DQL is now sent as `POST` with a JSON body.** `dql()`, `dql_parallel()` and
  their async twins keep the same names, options, defaults and return values;
  only the wire format changes: `POST {dql_url}?token=…` with
  `{"query", "size", "from"?, "format"?, "filter"?, "exportspec"?, …extra}`.
  The token stays in the query string; the query text no longer appears in the
  URL, and the URL-length limit on long queries is gone. `extra` is now typed
  `Mapping[str, Any]` (values go into the JSON body verbatim).
- `crawl()` failure now raises `JobError` (carrying the job name) instead of a
  synthesized `APIError(500, ...)`. `JobError` subclasses `APIError`.

#### Migration note: mocks and proxies

Test mocks keyed on `GET` and `?query=` stop matching. Before/after:

```python
# before (3.1.x)
def handler(request: httpx.Request) -> httpx.Response:
    assert request.method == "GET"
    assert request.url.params["query"] == "type:Organization"
    return httpx.Response(200, json={"data": []})

# after (3.2.0)
def handler(request: httpx.Request) -> httpx.Response:
    assert request.method == "POST"
    assert json.loads(request.content)["query"] == "type:Organization"
    return httpx.Response(200, json={"data": []})
```

GET-only proxies, caches, or a custom `dql_url` mirror may reject or not cache
POSTs. If you need the old wire format, use the low-level call (no new API):

```python
db.request("GET", db.dql_url, params={"token": db.token, "query": q, "size": 10})
```

or pin `diffbot<3.2`.

### Added

- Per-host base URL options: `api_base`, `kg_base`, `llm_base`, `nlp_base` on
  both `Diffbot` and `DiffbotAsync`. The older per-endpoint options
  (`analyze_url`, `crawler_url`, `llm_url`, `web_search_url`, `nlp_url`,
  `dql_url`, `ontology_url`) still work and win over the matching base when
  both are set.
- Repeated query parameters: handler param builders now declare
  `Sequence`-valued params explicitly (httpx already encoded them as repeated
  keys; this makes it a documented, tested capability).
- `client.request(method, url, ...)` on both clients: `DELETE` + arbitrary
  method/body/`Content-Type`, form-encoded (`data=`) and raw (`content=`)
  bodies, a per-call `timeout` override separate from the client default, and
  a `follow_redirects` override.
- A default-on retry policy (`RetryPolicy` dataclass, `retry` client option)
  for `429`/`5xx`/connection errors, with backoff, jitter, and `Retry-After`
  support, capped at 3 attempts by default. Disable with `retry=False`, or
  opt a single call out with `retryable=False` (used internally by
  `crawl_delete_job`/`crawl_delete_job_async`, a GET-shaped mutation that must
  never be retried blindly).
- `NotFoundError` (404) and `JobError`, both subclassing `APIError` so
  existing `except APIError` call sites are unaffected.
- `APIError.headers` (and subclasses), populated from the error response.
- Additive `TypedDict`/`Literal` type aliases in `diffbot.types`:
  `ChatMessage`, `ResponseFormat`, `ExportFormat`, `SnippetLength` — used in
  `ask()`/`ask_json()`/`dql()`/`web_search()` signatures. No Pydantic, no
  runtime behavior change.

### Fixed

- `ask()`/`ask_json()` (sync and async): a non-2xx response (e.g. 401, 429)
  while streaming now raises `AuthError`/`RateLimitError` as documented,
  instead of `httpx.ResponseNotRead`. The error body is now read before
  raising.
- `crawl()`'s job-failure path now raises `JobError` (carrying the job name)
  instead of a synthesized `APIError(500, ...)`.

### Internal

- Sync/async de-duplication: `Diffbot`/`DiffbotAsync._raise_for_status` and
  the repeated `client._http.get(...)` + raise pattern in every handler
  module are replaced by shared helpers in a new `_transport.py`, used by
  both clients through `client.request()`.
