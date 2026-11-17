# Phase 0 leftovers (Python)

Everything in the Phase 0 scope landed. This file records the items that are
deliberately smaller than the original plan's framing, and how each was resolved
under the reduced-scope coverage plan (`sdk-reduced/plan.md`). It mirrors the
TypeScript SDK's own `PHASE0_LEFTOVERS.md`.

## 1. Literal "endpoint registry" data structure: won't do

The original plan framed per-host base URLs as part of "an endpoint registry".
What landed is per-host base URL resolution (`api_base`/`kg_base`/`llm_base`/
`nlp_base`, with the older `*_url` options winning) directly in `client.py`, plus
an ad hoc `retryable=False` at the one call site that needs it
(`crawl_delete_job`). The reduced-scope plan adds no new API areas, so a
per-operation table would never get a second consumer. **Won't do.**

## 2. Success-path response headers: won't do (DQL reports cut)

Every *error* response's headers are attached to `APIError` (and subclasses) via
`headers`, populated in `_transport.raise_for_status()`. A generic opt-in for a
*successful* response's headers was only motivated by DQL coverage reports
(`X-Diffbot-CoverageReportId`), which are out of scope. **Won't do.**

## 3. `dql(raw=True)` binary correctness: no bug existed on the Python side

The TypeScript SDK corrupted `xls`/`xlsx` exports by re-encoding text. Python's
byte path (`response.content`) was already correct; no code change was needed.
Unchanged by the move to POST. Covered by the existing raw-mode tests.

## 4. Ontology parity: scheduled for S2

Adding `dql_fetch_ontology_text()` and `dql_refresh_ontology_async()` to close the
Python/TypeScript asymmetry is scheduled for **S2** (Python 3.4.0).

## 5. Response TypedDicts: landed in S1

Request-side `TypedDict`/`Literal` aliases landed in `src/diffbot/types.py` with Phase 0.
Response shapes (`DqlResponse`, `WebSearchResponse`, `ExtractResponse`, `CrawlJob`,
`AccountResponse`, `AskChunk`, ...) land in S1 (Python 3.3.0, branch `feat/sdk-s1`)
together with the pyright CI gate, so they are checked from day one.
