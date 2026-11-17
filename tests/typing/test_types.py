"""Type-level assertions, checked by ``pyright`` in CI (``uv run --extra dev pyright``).

``assert_type`` is a no-op at runtime, so these also run under pytest as a smoke test
that the calls themselves work against a mock transport.
"""
import json
from typing import TYPE_CHECKING, Any, AsyncIterator, Dict, Iterator, List, cast

import httpx

from diffbot import (
    AccountResponse,
    ArticleExtractResponse,
    CrawlDataRecord,
    CrawlJob,
    Diffbot,
    DiffbotAsync,
    DqlEntity,
    DqlResponse,
    EntitiesResponse,
    ExtractResponse,
    ImageExtractResponse,
    ProductExtractResponse,
    WebSearchResponse,
)

if TYPE_CHECKING:
    from typing_extensions import assert_type
else:

    def assert_type(val, typ, /):  # type: ignore[no-untyped-def]
        return val


def _handler(request: httpx.Request) -> httpx.Response:
    if request.url.path.endswith("/dql"):
        fmt = json.loads(request.content).get("format", "json")
        if fmt == "json":
            return httpx.Response(200, json={"hits": 1, "data": []})
        return httpx.Response(200, content=b'{"score": 1}\n' if fmt == "jsonl" else b"a,b\n")
    return httpx.Response(200, json={"objects": [], "jobs": [], "search_results": [], "entities": []})


db = Diffbot(token="t", transport=httpx.MockTransport(_handler))
adb = DiffbotAsync(token="t", transport=httpx.MockTransport(_handler))


def test_dql_overloads():
    assert_type(db.dql("q"), DqlResponse)
    assert_type(db.dql("q", format="json"), DqlResponse)
    assert_type(db.dql("q", size=0, from_=2, extra={"jsonmode": "extended", "n": 1}), DqlResponse)
    assert_type(db.dql("q", format="csv"), str)
    assert_type(db.dql("q", format="csv", raw=True), bytes)
    assert_type(db.dql("q", raw=True), bytes)
    assert_type(db.dql("q", format="xls"), bytes)
    assert_type(db.dql("q", format="xlsx"), bytes)
    assert_type(db.dql("q", format="jsonl"), Iterator[DqlEntity])
    hits: int = db.dql("q").get("hits", 0)
    assert hits == 1


async def _async_dql_types() -> None:
    assert_type(await adb.dql("q"), DqlResponse)
    assert_type(await adb.dql("q", format="csv"), str)
    assert_type(await adb.dql("q", format="xlsx"), bytes)
    assert_type(await adb.dql("q", raw=True), bytes)
    assert_type(await adb.dql("q", format="jsonl"), AsyncIterator[DqlEntity])


def test_extract_overloads():
    assert_type(db.extract("u"), ExtractResponse)
    assert_type(db.extract("u", "analyze", mode="article", fallback="product"), ExtractResponse)
    assert_type(db.extract("u", "article", fields=["links", "quotes"], max_tags=3), ArticleExtractResponse)
    assert_type(db.extract("u", "image", fields=["displayWidth"]), ImageExtractResponse)
    assert_type(db.extract("u", "my-custom-api"), ExtractResponse)
    assert_type(db.extract("u", "article", fmt="json", timeout=60000, extra={"proxy": "x"}), ArticleExtractResponse)


def test_other_response_types():
    assert_type(db.web_search("q"), WebSearchResponse)
    assert_type(db.entities("x"), EntitiesResponse)
    assert_type(db.crawl_list_jobs(), List[CrawlJob])
    assert_type(db.crawl_get_job("j"), CrawlJob)


def _crawl_download_and_account_types() -> None:
    assert_type(db.crawl_download("j"), List[CrawlDataRecord])
    assert_type(db.crawl_download("j", format="json", num=1), List[CrawlDataRecord])
    assert_type(db.crawl_download("j", format="csv", type="urls"), str)
    assert_type(db.account(), AccountResponse)
    assert_type(db.account(days=1), AccountResponse)
    assert_type(db.verify_token(), bool)


async def _async_misc_types() -> None:
    assert_type(await adb.web_search("q"), WebSearchResponse)
    assert_type(await adb.entities("x"), EntitiesResponse)
    assert_type(await adb.crawl_get_job("j"), CrawlJob)
    assert_type(await adb.crawl_download("j", format="csv"), str)
    assert_type(await adb.crawl_download("j"), List[CrawlDataRecord])
    assert_type(await adb.account(), AccountResponse)
    assert_type(await adb.verify_token(), bool)
    assert_type(await adb.extract("u", "product", fields=["meta"]), ProductExtractResponse)


def test_known_keys_type_check_and_cast_escape_hatch():
    resp = db.web_search("q")
    results = resp.get("search_results", [])
    assert results == []
    # undeclared keys: cast is the documented escape hatch
    loose = cast(Dict[str, Any], db.dql("q"))
    assert loose["hits"] == 1
