"""Type-level assertions, checked by ``pyright`` in CI (``uv run --extra dev pyright``).

``assert_type`` is a no-op at runtime, so these also run under pytest as a smoke test
that the calls themselves work against a mock transport.
"""
import json
import pathlib
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
    NlpResponse,
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
    assert_type(db.crawl_download("j", type="urls"), str)
    assert_type(db.account(), AccountResponse)
    assert_type(db.account(days=1), AccountResponse)
    assert_type(db.verify_token(), bool)


async def _async_misc_types() -> None:
    assert_type(await adb.web_search("q"), WebSearchResponse)
    assert_type(await adb.entities("x"), EntitiesResponse)
    assert_type(await adb.crawl_get_job("j"), CrawlJob)
    assert_type(await adb.crawl_download("j", format="csv"), str)
    assert_type(await adb.crawl_download("j", type="urls"), str)
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


def _dql_named_option_types() -> None:
    assert_type(db.dql("q", type="crawl", col="all", cluster="best", jsonmode="id"), DqlResponse)
    assert_type(db.dql("q", format="csv", exportseparator="|", exportfile="x.csv"), str)
    assert_type(db.dql("q", non_canonical_facts=True, no_dedup_articles=True, filter_exclude="a"), DqlResponse)
    db.dql("q", type="bogus")  # type: ignore[call-overload]
    db.dql("q", cluster="nope")  # type: ignore[call-overload]


def _nlp_types() -> None:
    assert_type(db.nlp("x"), NlpResponse)
    assert_type(db.nlp("x", fields=["summary", "language"], custom_summary={"max_number_of_sentences": 2}), NlpResponse)
    assert_type(db.entities("x"), EntitiesResponse)
    db.nlp("x", fields=["bogus"])  # type: ignore[list-item]
    db.nlp("x", format="html")  # type: ignore[arg-type]


async def _nlp_async_types() -> None:
    assert_type(await adb.nlp("x", format="plain text with title"), NlpResponse)


async def _ontology_text_types() -> None:
    assert_type(db.dql_fetch_ontology_text(), str)
    assert_type(await adb.dql_fetch_ontology_text(), str)
    assert_type(await adb.dql_refresh_ontology(pathlib.Path("o.json")), None)
