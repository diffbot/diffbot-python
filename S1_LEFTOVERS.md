# S1 leftovers (Python)

S1 (plan §5, §6, §8) landed on `feat/sdk-s1`. Notes on what is deliberately smaller than
the plan's wording, and what is unverified.

## Deliberately narrower

- **Overloads live on the client methods** (`Diffbot`/`DiffbotAsync` `dql`, `extract`,
  `crawl_download`), the public surface. The module-level shared implementations in
  `kg.py`/`extract.py`/`crawl.py` return `Any` to avoid duplicating ~50 overloads.
- **Per-API extract options use `**options: Unpack[...]` in the overloads** (a
  `TYPE_CHECKING`-only import of `typing_extensions.Unpack`; no runtime dependency).
  At runtime the implementation takes `**options` and rejects unknown names with
  `TypeError`. Every option is accepted for every API at runtime; only the type
  level restricts them per API.
- **Transport timeout is raised only when the caller sets `timeout`.** With the default
  30000 ms and the default 30 s client timeout the two are still equal, as before.
- `dql_parallel` returns `List[Any]` (heterogeneous per-call formats).
- `EntitiesResponse` mirrors TS `Pick<..., "entities" | "sentiment">`; `errors` is not declared.
- `CrawlDataRecord` is a best-effort shape (the crawl data JSON is example-only in the
  docs); keep it open to change. The TypeScript counterpart did not exist yet when this
  was written, so field-for-field parity with its `CrawlDataRecord` is unchecked.

## Unverified here

- Live tests (`pytest -m live`) were not run against the real API (no token resolved in
  the build environment); `test_live_verify_token_rejects_a_bad_token` was.
  The live crawl test (start/poll/download/delete) is therefore unexercised.
- Open question from plan §11: DQL POST parity (jsonl/csv/xlsx with `exportspec`,
  JSON strings vs numbers in `extra`) should be confirmed with the Diffbot contact
  before release.

## Not in S1 (see plan §2/§8)

S2 items (DQL named params, crawl-create options, `nlp()`, web-search multi-value
`text` + `snippet_length` validation, ontology text/async parity) and everything marked
Out.
