# Changelog

All notable changes to the `diffbot` Python package are documented here. The format
follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and the project uses
[Semantic Versioning](https://semver.org/).

## [3.4.1] - 2026-11-18

Same code as 3.4.1rc1, which was verified against diffbot-mcp CI.


### Fixed

- **`crawl(obey_robots=False)` and `crawl(use_proxies=False)` were silently ignored.**
  An explicit `False` was dropped instead of sent, so the API default applied (for
  `obeyRobots` that means robots.txt was still obeyed). Both are now tri-state like
  `use_canonical`: `None` (the new default) omits the param, `True`/`False` send `1`/`0`.
  Sync and async.
- **CLI `db crawl`:** `--obey-robots`/`--use-proxies` gain `--no-obey-robots`/
  `--no-use-proxies`, and `--restrict-domain` gains `--no-restrict-domain` (it could not be
  turned off before). Omitting the robots/proxies flags still leaves the API default.

## [3.4.0] - 2026-11-17

First release since 3.1.1 (and includes everything in it). It rolls up three development lines that were never
published on their own: the shared transport, sync/async de-duplication and DQL over
POST (planned as 3.2.0), response types plus `account`/`verify_token`/`crawl_download`/
extract options (3.3.0), and named options on existing endpoints plus `nlp()` (3.4.0).
No new Diffbot API areas are added.

### ⚠ Breaking changes

- **DQL is sent as `POST` with a JSON body.** `dql()`, `dql_parallel()` and their async
  twins keep the same signature and results, but mocks, proxies, or mirrors keyed on
  `GET` + `?query=` stop matching. See [Migrating DQL](#migrating-dql-mocks-and-proxies)
  below.
- **`crawl()` raises `APIError` when the create call answers HTTP 200 with
  `errorCode`/`error`** (for example errorCode 505, job name over 30 characters). It used
  to yield `JOB_CREATED` for a job that was never created. The error keeps the real
  status (200), body, and headers.
- **A `Retry-After` above `RetryPolicy.max_delay` (default 5.0 s) is no longer waited
  out or retried.** The call raises at once: `RateLimitError` with `retry_after` = raw
  header, or `APIError` with `headers["retry-after"]` for a 5xx (sync, async, and
  streamed). Raise `max_delay` to keep waiting.
- **Requests are now retried by default** (`429`, `5xx`, connection errors; 3 attempts
  with backoff and jitter). `crawl_delete_job` is never retried. Pass `retry=False` for
  the old single-attempt behavior.
- **`web_search(snippet_length=...)` is validated:** anything other than `short`,
  `medium`, `long`, `full` (case-insensitive) raises `ValidationError` instead of being
  sent upstream.
- **`dql()` raises `ValidationError` when `extra` repeats one of the new named options**
  (`type`, `col`, `filter_exclude`, ...).
- **Type-level:** `dql`, `extract`, `web_search`, `entities`, `crawl_list_jobs`,
  `crawl_get_job` return `TypedDict`s instead of `Dict[str, Any]`, and several methods
  gained `@overload`s. Runtime values are unchanged; a type checker may flag undeclared
  keys (escape hatch: `typing.cast(Dict[str, Any], resp)`).

### Added

- **Transport:** per-host base URLs (`api_base`, `kg_base`, `llm_base`, `nlp_base` on
  `Diffbot` and `DiffbotAsync`; the older `*_url` options still win when both are set);
  documented repeated query params; `client.request(method, url, ...)` with `DELETE`,
  form (`data=`) and raw (`content=`) bodies, a per-call `timeout`, and a
  `follow_redirects` override; the `RetryPolicy` dataclass and `retry` option with
  per-call `retryable=False`.
- **Errors:** `NotFoundError` (404) and `JobError`, both subclasses of `APIError`;
  `APIError.headers` from the error response.
- **Types:** request aliases (`ChatMessage`, `ResponseFormat`, `ExportFormat`,
  `SnippetLength`) and response `TypedDict`s exported from `diffbot` (`DqlResponse`/
  `DqlEntity`, `WebSearchResponse`/`WebSearchResult`, `EntitiesResponse`,
  `ExtractResponse` and per-API variants, `CrawlJob`, `CrawlDataRecord`,
  `AccountResponse`, `AskChunk`, ...). stdlib only, Python 3.9-compatible, no Pydantic.
- `account(days=None)` and `verify_token()` (sync and async) over `GET /v4/account`.
  `verify_token()` returns `False` only on an auth failure. The account response carries
  `token` and `childTokens`; don't log it whole.
- `crawl_download(name, *, format="json", type=None, num=None)` (sync and async) over
  `GET /v3/crawl/data`. `format="csv"` or `type="urls"` returns `str`, otherwise a list
  of records; a non-list JSON body (e.g. unknown job) raises `JobError`. The crawl
  watcher uses it. For tools that can't block: `crawl(..., watch=False)` ->
  `crawl_get_job` -> `crawl_download`.
- `extract()` keyword-only options: `timeout` (server-side ms, default 30000), `mode`,
  `fields` (per-API `Literal` names), `fallback`, `discussion`, `paging`, `max_pages`,
  `natural_language`, `summary_num_sentences`, `max_tags`, `tag_confidence`,
  `category_confidence`, `use_proxy`, and `extra` (`proxy`/`proxyAuth`; collisions with a
  named option or `token`/`url` raise `ValidationError`). Setting `timeout` raises the
  per-call transport timeout to at least `timeout + 10s`.
- `dql()`/`dql_async()` (and `dql_parallel`) keyword-only options `type` (`"query"`,
  `"text"`, `"queryTextFallback"`, `"crawl"`), `col`, `filter_exclude`,
  `exportseparator`, `exportfile`, `jsonmode`, `non_canonical_facts`,
  `no_dedup_articles`, `cluster`, sent in the POST body. `report` and `view` stay
  reachable via `extra`. Types: `DqlType`, `DqlJsonMode`, `DqlCluster`, `DqlOptions`.
- `crawl()` create options `url_crawl_regex`, `url_process_regex`,
  `page_process_pattern`, `max_to_crawl_per_subdomain`, `max_to_process_per_subdomain`,
  `use_canonical`, `notify_webhook`, `notify_email`; `custom_headers` accepts a string or
  a sequence (repeated params). The 30-character job-name limit is documented.
- `nlp(text, *, fields, lang, format, document_type, custom_summary)` (sync and async) on
  the existing NL endpoint, single document. `entities()` is unchanged. Types:
  `NlpField`, `NlpFormat`, `NlpCustomSummary`, `NlpResponse`.
- `web_search(text=...)` accepts a string or 1-5 strings (repeated `text=`);
  out-of-range lengths raise `ValidationError` before any request.
- `dql_fetch_ontology_text()` (sync and async); `dql_refresh_ontology` on
  `DiffbotAsync` (module function `diffbot.kg.dql_refresh_ontology_async`).
- Dev: `pyright` gate (basic on `src/`, strict on `types.py`, plus `tests/typing`) in CI;
  live test workflow (push to `main`, manual dispatch, twice-monthly cron; never on PRs).

### Changed

- `dql()` request shape: `POST {dql_url}?token=…` with `{"query", "size", "from"?,
  "format"?, "filter"?, "exportspec"?, …extra}`. The token stays in the query string;
  the query text no longer appears in URLs, and the URL length limit is gone. `extra` is
  typed `Mapping[str, Any]` and its values go into the JSON body verbatim.
- A failed crawl job raises `JobError` (carrying the job name) instead of a synthesized
  `APIError(500, ...)`. `JobError` subclasses `APIError`, so `except APIError` still
  catches it.
- Internal: shared sync/async transport helpers in `_transport.py` replace the
  per-handler `_http.get(...)` + raise pattern.

### Fixed

- `ask()`/`ask_json()` (sync and async): a non-2xx response while streaming raises
  `AuthError`/`RateLimitError`/`APIError` as documented instead of
  `httpx.ResponseNotRead`.
- `dql(format="csv")` and `dql(format="jsonl")` without `raw=True` crashed in
  `response.json()`. `csv` now returns `str`, `xls`/`xlsx` return `bytes`, and `jsonl`
  returns an iterator of entities (`AsyncIterator` on the async client).
- `crawl()` no longer reports `JOB_CREATED` for a create that failed with HTTP 200 +
  `errorCode`.
- `APIError.message` falls back to the body's `error` field (the `{errorCode, error}`
  shape), matching the TypeScript SDK.
- `Retry-After: inf` no longer crashes `time.sleep` with `OverflowError`; non-finite
  values fall back to backoff.

### Known limitations

- `extra` can still override the pre-existing DQL keys (`size`, `from`, `format`,
  `filter`, `exportspec`); only the new named keys are collision-checked.
- `crawl()` has no `extra`; recurring-crawl admin (`repeat`, `maxRounds`, ...) is not
  exposed. `Diffbot.crawl(**kwargs)` does not type-check the new create options.
- `nlp()` returns one `NlpResponse` `TypedDict` (all fields optional), not a per-`fields`
  type. `custom_summary` reads only the Python key `max_number_of_sentences`.
- `crawl_get_job` still returns `{}` for a missing job (the TypeScript SDK returns
  `undefined`).
- No generic success-path response headers.

### Migrating DQL: mocks and proxies

Test mocks keyed on `GET` and `?query=` stop matching. Before/after:

```python
# before (3.1.x)
def handler(request: httpx.Request) -> httpx.Response:
    assert request.method == "GET"
    assert request.url.params["query"] == "type:Organization"
    return httpx.Response(200, json={"data": []})

# after (3.4.0)
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

or pin `diffbot<3.4` (3.1.x).
