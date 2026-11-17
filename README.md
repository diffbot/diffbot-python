# Diffbot Python Library

> ⚠️ **The PyPI package is now [`diffbot`](https://pypi.org/project/diffbot/)** (`pip install diffbot`).
> `diffbot-python` is legacy and its final release (0.3.0) will never be updated.
> See [Installation](#installation) to migrate.

Python client library for [Diffbot](https://www.diffbot.com) APIs.


## Installation

Install the [standalone CLI binary](#standalone-binary) for [agentic use](#how-to-use-with-an-agent):

```bash
curl -fsSL https://raw.githubusercontent.com/diffbot/diffbot-python/main/install.sh | sh
```

If you prefer, the full Python library can also be installed with pip:

```bash
python3 -m pip install diffbot
```

> This package was formerly published as `diffbot-python`, whose final release (0.3.0) gets no further updates.
> If you're upgrading from it, run `pip uninstall diffbot-python && pip install --force-reinstall diffbot`
> and replace `diffbot-python` with `diffbot` in your requirements.

For local development:

```bash
pip install -e ".[dev]"
```

## Usage

### Authentication

The CLI and the library can share a single credential. The token always has to be
passed to the client explicitly, but `resolve_token()` gives you the same lookup the
CLI uses, in this order:

1. An explicit token passed to `resolve_token(token)`.
2. The `DIFFBOT_API_TOKEN` environment variable.
3. A `DIFFBOT_API_TOKEN=...` line in `~/.diffbot/credentials`.

Set it once and it works for both the CLI and your scripts. Either export it:

```bash
export DIFFBOT_API_TOKEN=<TOKEN>
```

…or write it to the shared credentials file (handy for keeping it out of your shell environment):

```bash
mkdir -p ~/.diffbot
printf 'DIFFBOT_API_TOKEN=%s\n' '<TOKEN>' > ~/.diffbot/credentials
chmod 600 ~/.diffbot/credentials
```

With either in place, resolve the token and pass it to the client:

```python
from diffbot import Diffbot, resolve_token

db = Diffbot(token=resolve_token())  # from env var or ~/.diffbot/credentials
data = db.extract("https://www.example.com")
```

### Client configuration

`Diffbot` and `DiffbotAsync` take the same keyword arguments — the client is the single
place to configure the SDK.

| Argument | Default | Used by |
|----------|---------|---------|
| `token` | — (required) | all |
| `timeout` | `30.0` (seconds) | all |
| `retry` | on, 3 attempts | all; `False` disables, or pass a `RetryPolicy` to tune it |
| `transport` | httpx default | all |
| `api_base` | `https://api.diffbot.com` | `extract`, `crawl`, `crawl_list_jobs`, `crawl_get_job`, `crawl_delete_job` |
| `kg_base` | `https://kg.diffbot.com` | `dql`, `dql_parallel`, `dql_fetch_ontology`, `dql_refresh_ontology` |
| `llm_base` | `https://llm.diffbot.com` | `ask`, `ask_json`, `web_search` |
| `nlp_base` | `https://nl.diffbot.com` | `entities` |
| `analyze_url` | derived from `api_base` | `extract` |
| `crawler_url` | derived from `api_base` | `crawl`, `crawl_list_jobs`, `crawl_get_job`, `crawl_delete_job` |
| `llm_url` | derived from `llm_base` | `ask`, `ask_json` |
| `web_search_url` | derived from `llm_base` | `web_search` |
| `nlp_url` | derived from `nlp_base` | `entities` |
| `dql_url` | derived from `kg_base` | `dql`, `dql_parallel` |
| `ontology_url` | derived from `kg_base` | `dql_fetch_ontology`, `dql_refresh_ontology` |

```python
from diffbot import Diffbot

db = Diffbot(
    token="YOUR_TOKEN",
    timeout=60.0,
    dql_url="http://localhost:8080/kg/v3/dql",
)
```

Point the whole SDK at a staging environment with one option instead of one per endpoint:

```python
staging = Diffbot(token="YOUR_TOKEN", api_base="https://staging.example.com")
```

`api_base`/`kg_base`/`llm_base`/`nlp_base` set the host for every endpoint on that host
at once. The older per-endpoint options (`analyze_url`, `crawler_url`, `llm_url`,
`web_search_url`, `nlp_url`, `dql_url`, `ontology_url`) still work and win over the
matching base when both are set; `analyze_url` is a base the SDK appends `/{api}` to,
`crawler_url` is used as given for job management and with `/data` appended for crawl
results, and the rest are complete endpoints used as given.

Requests retry `429` and `5xx` responses (and connection errors) with backoff and
jitter, honoring a `Retry-After` header, by default. Disable retries or tune the policy:

```python
from diffbot import Diffbot, RetryPolicy

db = Diffbot(token="YOUR_TOKEN", retry=False)
# or: retry=RetryPolicy(max_attempts=5)
```

The transport also accepts a per-call `retryable=False` escape hatch; the SDK uses it
internally for `crawl_delete_job`, a GET-shaped mutation that must not be retried
blindly.

Passing `transport` replaces the httpx transport, which is the hook for proxies or
mocking in tests. `Diffbot` takes an `httpx.BaseTransport`, `DiffbotAsync` an
`httpx.AsyncBaseTransport`:

```python
import httpx
from diffbot import Diffbot

db = Diffbot(token="YOUR_TOKEN", transport=httpx.HTTPTransport(retries=3))
```

### Extract structured content
```python
from diffbot import Diffbot

db = Diffbot(token="YOUR_TOKEN")
data = db.extract("https://www.example.com")

# Optional keyword-only options (per-API field names are type-checked):
article = db.extract(
    "https://www.example.com/post",
    "article",
    fmt="json",
    timeout=60000,  # server-side fetch timeout in ms (default 30000)
    fields=["links", "quotes"],
    max_tags=5,
)
```

`timeout` is the Diffbot-side fetch timeout in milliseconds; the SDK raises the HTTP transport timeout to at least `timeout + 10s` so the client never aborts first. `mode` overrides the `fmt="markdown"` → `mode=llm` mapping, and `extra={"proxy": ..., "proxyAuth": ...}` passes anything not named.

### Ask Diffbot LLM
```python
from diffbot import Diffbot

db = Diffbot(token="YOUR_TOKEN")
for chunk in db.ask([{"role": "user", "content": "What's the capital of France?"}]):
    print(chunk, end="")
```

### Structured output
Pass a JSON Schema to constrain the answer. The model is held to the schema by a grammar during decoding, so the result parses reliably even though the answer is retrieved live from the web.

```python
from diffbot import Diffbot

db = Diffbot(token="YOUR_TOKEN")
schema = {
    "type": "object",
    "properties": {
        "country": {"type": "string"},
        "capital": {"type": "string"},
    },
    "required": ["country", "capital"],
}
answer = db.ask_json([{"role": "user", "content": "What's the capital of France?"}], schema)
print(answer["capital"])
```

Omit the schema to let the model choose the shape, or use `ask` with `response_format` to stream a constrained answer:

```python
from diffbot import Diffbot, json_schema_format

db = Diffbot(token="YOUR_TOKEN")
answer = db.ask_json([{"role": "user", "content": "What's the capital of France?"}])

for chunk in db.ask(
    [{"role": "user", "content": "What's the capital of France?"}],
    response_format=json_schema_format(schema),
):
    print(chunk, end="")
```

> **Avoid `response_format={"type": "json_object"}`.** The endpoint accepts it, but applies no grammar to it — the RAG loop's internal tool call is itself a JSON object, so it can be returned as the final answer. This is reproducible whenever the request includes a system message. `ask_json` therefore defaults to a permissive JSON Schema instead, and raises `ValidationError` if it ever sees a tool call come back.

### Crawl a site for structured content
```python
from diffbot import Diffbot

db = Diffbot(token="YOUR_TOKEN")
for event in db.crawl("https://www.example.com", hops=1):
    print(event)
```

Job names are limited to 30 characters. The crawler reports a create failure such as an overlong name as HTTP 200 with an `errorCode` in the body; `crawl()` raises `APIError` for it rather than yielding `JOB_CREATED`.

For tools that can't block on a long crawl, start the job without watching, poll it, then download the results:

```python
import time
from diffbot import Diffbot

db = Diffbot(token="YOUR_TOKEN")
for _ in db.crawl("https://www.example.com", job_name="my-crawl", hops=1):
    pass  # watch=False (the default): only creates the job

while db.crawl_get_job("my-crawl").get("jobStatus", {}).get("status", 0) in (0, 7):
    time.sleep(5)  # 0 initializing, 7 in progress; 9 complete

records = db.crawl_download("my-crawl")  # list of extracted records
csv_text = db.crawl_download("my-crawl", format="csv")  # str
```

`crawl_get_job` returns `{}` for a job that doesn't exist (the TypeScript SDK returns `undefined`).

### Query the Knowledge Graph
```python
from diffbot import Diffbot

db = Diffbot(token="YOUR_TOKEN")
results = db.dql('type:Organization name:"Diffbot"')

# The return type follows `format`: DqlResponse (json), str (csv), bytes (xls/xlsx
# or raw=True), or an iterator of entities (jsonl).
csv_text = db.dql('type:Organization name:"Diffbot"', size=5, format="csv")
for entity in db.dql('type:Organization name:"Diffbot"', size=5, format="jsonl"):
    print(entity["entity"]["name"])
```

### Account and token check
```python
from diffbot import Diffbot

db = Diffbot(token="YOUR_TOKEN")
if not db.verify_token():  # True/False; only an auth failure means False
    raise SystemExit("Diffbot token rejected")
usage = db.account(days=7).get("usage", [])  # free call; never print the whole response
```

### Web Search
```python
from diffbot import Diffbot

db = Diffbot(token="YOUR_TOKEN")
results = db.web_search("diffbot knowledge graph")
for r in results["search_results"]:
    print(r["score"], r["title"], r["pageUrl"])
    print(r["content"])

# snippet_length controls how much of each page comes back in "content":
# "short" (~1-1.5 KB per result), "medium", "long" (default), or "full"
results = db.web_search("diffbot knowledge graph", num_results=5, snippet_length="short")

# 1-5 queries in one call (sent as repeated text= params); 0 or >5 raises ValidationError
results = db.web_search(["diffbot knowledge graph", "diffbot crawl api"], num_results=3)

# "full" with a url: query returns the whole stored page
page = db.web_search("url:https://en.wikipedia.org/wiki/Knowledge_graph", snippet_length="full")
```

### Entities (NLP)
```python
from diffbot import Diffbot

db = Diffbot(token="YOUR_TOKEN")
result = db.entities("Apple CEO Tim Cook announced record quarterly earnings.")
for entity in result["entities"]:
    print(entity["name"], entity.get("type"), entity.get("id"))
print("sentiment:", result.get("sentiment"))
```

### NLP: other fields (`nlp`)
`entities()` always requests `entities` and `sentiment`. `nlp()` reaches the rest of the
same endpoint for a single document.
```python
from diffbot import Diffbot

db = Diffbot(token="YOUR_TOKEN")
result = db.nlp(
    "Acme Launches Rocket\n\nAcme announced a new rocket today.",
    fields=["summary", "categories", "language"],
    format="plain text with title",
    document_type="news article",
    custom_summary={"max_number_of_sentences": 1},
)
print(result.get("summary"))
```

## Async Usage

### Extract structured content
```python
import asyncio
from diffbot import DiffbotAsync

async def main():
    async with DiffbotAsync(token="YOUR_TOKEN") as db:
        data = await db.extract("https://www.example.com")
        print(data)

        article = await db.extract(
            "https://www.example.com/post", "article", fmt="json", timeout=60000, fields=["links"]
        )

asyncio.run(main())
```

### Ask Diffbot LLM
```python
import asyncio
from diffbot import DiffbotAsync

async def main():
    async with DiffbotAsync(token="YOUR_TOKEN") as db:
        async for chunk in db.ask([{"role": "user", "content": "What's the capital of France?"}]):
            print(chunk, end="")

asyncio.run(main())
```

### Structured output
```python
import asyncio
from diffbot import DiffbotAsync

schema = {
    "type": "object",
    "properties": {
        "country": {"type": "string"},
        "capital": {"type": "string"},
    },
    "required": ["country", "capital"],
}

async def main():
    async with DiffbotAsync(token="YOUR_TOKEN") as db:
        answer = await db.ask_json(
            [{"role": "user", "content": "What's the capital of France?"}], schema
        )
        print(answer["capital"])

asyncio.run(main())
```

### Crawl a site for structured content
```python
import asyncio
from diffbot import DiffbotAsync

async def main():
    async with DiffbotAsync(token="YOUR_TOKEN") as db:
        async for event in db.crawl("https://www.example.com", hops=1):
            print(event)

asyncio.run(main())
```

Start, poll, then download, without blocking inside one call:

```python
import asyncio
from diffbot import DiffbotAsync

async def main():
    async with DiffbotAsync(token="YOUR_TOKEN") as db:
        async for _ in db.crawl("https://www.example.com", job_name="my-crawl", hops=1):
            pass  # watch=False (the default): only creates the job
        while (await db.crawl_get_job("my-crawl")).get("jobStatus", {}).get("status", 0) in (0, 7):
            await asyncio.sleep(5)
        records = await db.crawl_download("my-crawl")
        csv_text = await db.crawl_download("my-crawl", format="csv")

asyncio.run(main())
```

### Query the Knowledge Graph
```python
import asyncio
from diffbot import DiffbotAsync

async def main():
    async with DiffbotAsync(token="YOUR_TOKEN") as db:
        results = await db.dql('type:Organization name:"Diffbot"')
        print(results)

        csv_text = await db.dql('type:Organization name:"Diffbot"', size=5, format="csv")
        async for entity in await db.dql('type:Organization name:"Diffbot"', size=5, format="jsonl"):
            print(entity["entity"]["name"])

asyncio.run(main())
```

### Account and token check
```python
import asyncio
from diffbot import DiffbotAsync

async def main():
    async with DiffbotAsync(token="YOUR_TOKEN") as db:
        if not await db.verify_token():
            raise SystemExit("Diffbot token rejected")
        usage = (await db.account(days=7)).get("usage", [])

asyncio.run(main())
```

### Web Search
```python
import asyncio
from diffbot import DiffbotAsync

async def main():
    async with DiffbotAsync(token="YOUR_TOKEN") as db:
        results = await db.web_search("diffbot knowledge graph")
        for r in results["search_results"]:
            print(r["score"], r["title"], r["pageUrl"])
            print(r["content"])

asyncio.run(main())
```

### Entities (NLP)
```python
import asyncio
from diffbot import DiffbotAsync

async def main():
    async with DiffbotAsync(token="YOUR_TOKEN") as db:
        result = await db.entities("Apple CEO Tim Cook announced record quarterly earnings.")
        for entity in result["entities"]:
            print(entity["name"], entity.get("type"), entity.get("id"))
        print("sentiment:", result.get("sentiment"))

asyncio.run(main())
```

## CLI

This library also includes a CLI exposed as the `db` command.

To make `db` available from anywhere, install it as an isolated tool with [uv](https://docs.astral.sh/uv/):

```bash
uv tool install .
```

This drops a `db` executable into `~/.local/bin` (ensure it is on your `PATH`). Use `--force` to reinstall or upgrade after changes, or `--editable` to have source edits take effect immediately. Alternatively, a plain `pip install .` (or `pip install -e .`) also installs the `db` entry point into the active environment.

### Standalone binary

Every release also ships a self-contained `db` binary for Linux (x86_64 and aarch64) and macOS (Apple Silicon) as a Python-free option. The installer detects your platform, verifies the SHA256 checksum, and installs (or upgrades) `db` into `~/.local/bin`:

```bash
curl -fsSL https://raw.githubusercontent.com/diffbot/diffbot-python/main/install.sh | sh
```

Pin a specific release or install location with flags (or the `DB_VERSION` / `DB_INSTALL_DIR` environment variables); re-running the installer upgrades an existing install in place:

```bash
curl -fsSL https://raw.githubusercontent.com/diffbot/diffbot-python/main/install.sh | sh -s -- --version v0.2.1 --bin-dir ~/bin
```

### How to use

```bash
export DIFFBOT_API_TOKEN=your-token-here

db extract https://www.example.com
db ask "What's the capital of France?"
db ask "What's the capital of France?" --json
db ask "What's the capital of France?" --schema capital.json
db crawl https://www.example.com --hops 1
db crawl-list-jobs
db crawl-delete-job crawl-1234567890
db web-search "diffbot knowledge graph"
db web-search "diffbot knowledge graph" -n 5 -f json
db web-search "diffbot knowledge graph" -n 5 -s short
db web-search "url:https://en.wikipedia.org/wiki/Knowledge_graph" -s full -f json
db entities "Apple CEO Tim Cook announced record quarterly earnings."
db entities "Apple CEO Tim Cook announced record quarterly earnings." -f dql
```

### How to use with an agent
Once installed, this library will work alongside [`diffbot-skills`](https://github.com/diffbot/diffbot-skills) to enable your agent full access to structuring web knowledge with Diffbot. Diffbot Agent Skills even unlocks some additional skills like crafting DQL from natural language. 

`diffbot-skills` will pick up or install this library automatically. 


## Tests

Run the mock test suite:
```bash
python -m pytest
```

Run live integration tests against the real API (requires a valid token).
The token is resolved the same way as everywhere else — the `DIFFBOT_API_TOKEN`
environment variable or `~/.diffbot/credentials`:
```bash
DIFFBOT_API_TOKEN=your_token python -m pytest -m live
```

## Acknowledgements

Thanks to [@attilaolah](https://github.com/attilaolah), who published the original `diffbot` package in 2012 and looked after the name for 14 years.
