# S2 leftovers (Python)

S2 (plan §2, §6, §8; Python 3.4.0) landed on `feat/sdk-s2`, stacked on `feat/sdk-s1`.
`pyproject.toml` is not bumped (release-time).

## Landed

- DQL named params (`type`, `col`, `filter_exclude`, `exportseparator`, `exportfile`,
  `jsonmode`, `non_canonical_facts`, `no_dedup_articles`, `cluster`), POST body, `extra`
  collision -> `ValidationError`, forwarded by `dql_parallel`.
- Crawl-create named options and `custom_headers: str | Sequence[str]`.
- `nlp()` (sync/async) on the NL endpoint; `entities()` untouched.
- Web search: 1-5 `text` values, `snippet_length` validation.
- Ontology: `dql_fetch_ontology_text`, `dql_refresh_ontology_async`.
- Live cases: web search (single/2-value `text`), entities + nlp.

## Deliberately narrower than the plan

- **DQL overloads use `**options: Unpack[DqlOptions]`** (type-level only, like extract);
  the implementation has explicit keyword parameters.
- **`extra` collision applies to the new named keys only.** Existing keys (`size`,
  `from`, `format`, `filter`, `exportspec`) can still be overridden through `extra`, as
  before; changing that would be a behaviour change outside S2. A named option whose
  value is `None` does not collide, so `extra={"jsonmode": ...}` keeps working.
- **`crawl()` has no `extra`**, so `repeat`/`maxRounds`/`seedRecrawlFrequency`/
  `onlyProcessIfNew` are simply unreachable (per the task, no new backdoor).
  `Diffbot.crawl` still takes `**kwargs: Any`, so the new names are not type-checked
  there. `use_canonical` is sent as `1`/`0` only when set.
- **`nlp()` response is one `NlpResponse` TypedDict** (all fields optional), not a
  per-`fields` `Pick`. `facts`/`records`/`categories`/`sentences` are `List[Any]`.
  `custom_summary` uses the Python key `max_number_of_sentences` (wire
  `maxNumberOfSentences`); the 1-10 range is left to the server.
- **Async refresh naming:** on `DiffbotAsync` it is `dql_refresh_ontology` (no suffix,
  like `dql_fetch_ontology`); `dql_refresh_ontology_async` is the `diffbot.kg` function.
- `snippet_length` stays typed as the lowercase `SnippetLength` Literal; uppercase input
  is accepted at runtime only.
- `crawl_get_job` still returns `{}` for a missing job (TS: `undefined`); unchanged.

## Unverified

- Live tests (`pytest -m live`) were not run in this session, including the two new
  cases. Not confirmed against the real API: `nlp()` `documentType`/`customSummary`
  placement inside the document object (taken from the docs), repeated `text=` on the
  live web search endpoint, repeated `customHeaders` on the crawl create, and
  `type=crawl` DQL requests.
- The TypeScript S2 counterpart was not present when this was written, so field-for-field
  parity (names, validation messages) is unchecked beyond `snippetLength`.
- Plan §11 open question about DQL POST parity is still open (see `S1_LEFTOVERS.md`).
