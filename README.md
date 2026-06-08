# Diffbot Python Library

Python client library for [Diffbot](https://www.diffbot.com) APIs.


## Installation

Install the [standalone CLI binary](#standalone-binary) for [agentic use](#how-to-use-with-an-agent):

```bash
curl -fsSL https://raw.githubusercontent.com/diffbot/diffbot-python/main/install.sh | sh
```

If you prefer, the full Python library can also be installed with pip:

```bash
python3 -m pip install diffbot-python
```

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
db crawl https://www.example.com --hops 1
db crawl-list-jobs
db crawl-delete-job crawl-1234567890
db web-search "diffbot knowledge graph"
db web-search "diffbot knowledge graph" -n 5 -f json
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
