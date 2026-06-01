# Diffbot Python Library

Python client library for [Diffbot](https://www.diffbot.com) APIs.


## Installation

```bash
pip install git+https://github.com/diffbot/diffbot-python.git
```

Or, for local development:

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

### Extract structured content
```python
from diffbot import Diffbot

db = Diffbot(token="YOUR_TOKEN")
data = db.extract("https://www.example.com")
```

### Ask Diffbot LLM
```python
from diffbot import Diffbot

db = Diffbot(token="YOUR_TOKEN")
for chunk in db.ask([{"role": "user", "content": "What's the capital of France?"}]):
    print(chunk, end="")
```

### Crawl a site for structured content
```python
from diffbot import Diffbot

db = Diffbot(token="YOUR_TOKEN")
for event in db.crawl("https://www.example.com", hops=1):
    print(event)
```

### Query the Knowledge Graph
```python
from diffbot import Diffbot

db = Diffbot(token="YOUR_TOKEN")
results = db.dql('type:Organization name:"Diffbot"')
```

### Web Search
```python
from diffbot import Diffbot

db = Diffbot(token="YOUR_TOKEN")
results = db.web_search("diffbot knowledge graph")
for r in results["search_results"]:
    print(r["score"], r["title"], r["pageUrl"])
    print(r["content"])
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

## Async Usage

### Extract structured content
```python
import asyncio
from diffbot import DiffbotAsync

async def main():
    async with DiffbotAsync(token="YOUR_TOKEN") as db:
        data = await db.extract("https://www.example.com")
        print(data)

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

### Query the Knowledge Graph
```python
import asyncio
from diffbot import DiffbotAsync

async def main():
    async with DiffbotAsync(token="YOUR_TOKEN") as db:
        results = await db.dql('type:Organization name:"Diffbot"')
        print(results)

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

```bash
export DIFFBOT_API_TOKEN=your-token-here

db extract https://www.example.com
db ask "What's the capital of France?"
db crawl https://www.example.com --hops 1
db crawl-list-jobs
db crawl-delete-job crawl-1234567890
db web-search "diffbot knowledge graph"
db web-search "diffbot knowledge graph" -n 5 -f json
db entities "Apple CEO Tim Cook announced record quarterly earnings."
db entities "Apple CEO Tim Cook announced record quarterly earnings." -f dql
```

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
