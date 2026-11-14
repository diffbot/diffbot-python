# Phase 0 leftovers (Python)

Everything in the Phase 0 scope (`py-prompt.md`, opus-plan.md §6 "Phase 0 — Foundation",
§3.2–3.4, §3.7) landed. A few items are deliberately smaller than the plan's framing, or
were already true on the Python side without a code change — documented here rather than
silently shipped (or silently skipped) without explanation, mirroring the TypeScript
SDK's own `PHASE0_LEFTOVERS.md` on this branch.

## 1. No literal "endpoint registry" data structure

opus-plan §3.2/§6 0.1 frames the per-host base URLs as part of "an endpoint registry +
per-host base URLs." What landed is the per-host base URL resolution
(`api_base`/`kg_base`/`llm_base`/`nlp_base`, old `*_url` options winning aliases) directly
in `client.py` — there's no separate data structure mapping `(operation) -> {path,
auth_style, retryable}`.

This mirrors the TypeScript SDK's same call on this branch: Phase 0 adds zero new
endpoints, so the only thing a registry would currently serve is base-URL resolution
(done) and a `retryable` flag (done ad hoc, as an explicit `retryable=False` at the one
call site that needs it — `crawl_delete_job`/`crawl_delete_job_async`). Building a
generic per-operation table with no second or third consumer risked guessing the wrong
shape for Phase 1+ (Account, Enhance, Bulk, Custom API, ...), which is where a real
registry starts paying for itself. Revisit when Phase 1 lands.

## 2. Response headers: error path only, not success path

opus-plan §6 0.6 asks for "response headers surfaced to callers," calling out an
`include_headers` option or a `*_raw` variant returning `(body, headers)`.

What landed: every error response's headers are attached to `APIError` (and its
subclasses `AuthError`, `NotFoundError`, `RateLimitError`, `JobError`) via a new
`headers` field, populated in `_transport.raise_for_status()`. Tested in
`tests/test_transport.py`'s `raise_for_status` tests.

What didn't land: a generic opt-in mechanism for a *successful* response's headers. The
plan's own stated motivation is `X-Diffbot-CoverageReportId` on a DQL coverage report
(opus-plan §3.4, §6 0.6's "prerequisite for DQL coverage reports") — that's a Phase 6
operation (`dql_report`) that doesn't exist yet. Building the success-path mechanism now,
with no real caller to shape it against, risked the same guessing problem as the
registry above. Build it alongside `dql_report`/`dql_report_by_id` in Phase 6. Matches
the TypeScript SDK's identical call on this branch.

## 3. `dql(raw=True)` binary correctness: no bug existed on the Python side

opus-plan §3.3/§6 0.5 frames this as "binary + text response reads" plus a concrete bug:
the TypeScript SDK's `dql()` read the body as text and re-encoded it with
`TextEncoder`, corrupting `xls`/`xlsx` exports. The audit explicitly notes Python's byte
path was already correct (`kg.py` returning `response.content` directly). No code change
was needed here beyond routing the call through the shared `client.request()` helper,
which preserves the same `response.content` / `response.json()` split. Covered by the
existing `test_dql.py` raw-mode tests (unchanged) plus the new per-host-base tests.

## 4. Ontology asymmetries are Phase 1, not Phase 0

opus-plan §5.2's core-surface-mapping row for the ontology endpoint lists adding
`dql_fetch_ontology_text()` and `dql_refresh_ontology_async()` to close the existing
Python/TypeScript asymmetry (`dql_refresh_ontology` has no async twin; TypeScript has no
raw-text fetch). That row is scoped under "Phase 1 — Account + token verification," not
Phase 0, and the `py-prompt.md` Phase 0 scope list does not mention it. Left alone.

## 5. TypedDict/Literal annotations: existing-surface request parameters only

`py-prompt.md` asks for "matching TypedDict(total=False)/Literal annotations, additive,
no Pydantic" as the Python counterpart to the TypeScript SDK's much larger Phase 0 type
safety push (vendored OpenAPI, generated response schemas, per-handler overloads). The
typesafety-revision page's override on this point is specifically about TypeScript's
approach; opus-plan's own phasing (§6, Phase 7 "typed responses... land as a dedicated
minor, not bundled with each endpoint" — the risk being a `TypedDict` claiming a field
that a future server response omits) argues for keeping Python's response shapes as
plain `dict`/`bytes` for now, which is what shipped.

What landed: `src/diffbot/types.py` adds `ChatMessage`, `ResponseFormatType`,
`ResponseFormat`, `ExportFormat`, `SnippetLength`, and `CrawlJobStatusCode` (the last
documents the numeric status codes `crawl.py` already branches on; not yet wired into a
public signature since no handler takes a status code as an input). These are wired into
the existing `ask()`/`ask_json()`/`dql()`/`web_search()` request-parameter signatures in
both `client.py` and the handler modules — purely additive, no runtime behavior change
(verified by the full test suite staying green before and after).

What didn't land: `TypedDict` overlays for *response* shapes (`DqlResponse`,
`WebSearchResponse`, `NlpResponse`, `ExtractResponse`, a `CrawlJob`/`JobStatus` pair,
`Ontology`'s wire format). This repo has no mypy/type-checking gate in CI today (checked
`.github/workflows/tests.yml`), so there is no second consumer to shape these against
yet, and retrofitting them risks exactly the staleness opus-plan §3.5/§6 Phase 7 warns
about. Revisit if/when Enhance (Phase 2) introduces the first genuinely new typed
response and a type-checking CI gate is added.

## Everything else

The sync/async de-duplication refactor (shared `_transport.py` request/response
helpers), per-host bases, repeated query parameters, DELETE + arbitrary method/body/
Content-Type, form-encoded and raw bodies, per-call timeout, the default-on retry policy
with per-call `retryable=False` opt-out, `NotFoundError`/`JobError` (both subclassing
`APIError`), and the streaming `ask()` `ResponseNotRead` fix (sync and async, with tests
using a real byte-stream mock transport so the fix is actually exercised) all landed —
see the commit log for the breakdown and `tests/test_transport.py`, `tests/test_client.py`,
`tests/test_ask.py`, `tests/test_crawl.py`, `tests/test_dql.py` for coverage.

The TypeScript SDK's two fixes (dql raw-mode binary corruption, crawl CSV quote-aware
parsing) and its full type-safety push (vendored OpenAPI, generated types, per-handler
overloads, typescript-eslint strict-type-checked) are not part of this checkout; they
were implemented first on the matching TypeScript branch per the assignment.
