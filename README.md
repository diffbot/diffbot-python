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
Set your Diffbot API token in your environment or .env.

```bash
export DIFFBOT_API_TOKEN=<TOKEN>
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

This library also includes a CLI.

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

Run live integration tests against the real API (requires a valid token):
```bash
DIFFBOT_TOKEN=your_token python -m pytest -m live
```
