"""Cheap live checks against the real API (``pytest -m live``).

Skipped by default. Assertions are on response *shape* only, never web content.
Never include token values in assertion messages.
"""
import time
import uuid

import pytest

pytestmark = pytest.mark.live


def test_live_dql_post_hit_count(db):
    result = db.dql("type:Organization name:Diffbot", size=0)
    assert isinstance(result, dict)
    assert "hits" in result


def test_live_dql_post_single_read(db):
    result = db.dql('type:Organization name:"Diffbot"', size=1)
    assert len(result["data"]) == 1


def test_live_dql_post_csv(db):
    text = db.dql('type:Organization name:"Diffbot"', size=1, format="csv")
    assert isinstance(text, str) and len(text.splitlines()) >= 2
    assert isinstance(db.dql('type:Organization name:"Diffbot"', size=1, format="csv", raw=True), bytes)


def test_live_dql_post_jsonl(db):
    entities = list(db.dql('type:Organization name:"Diffbot"', size=1, format="jsonl"))
    assert len(entities) >= 1


def test_live_dql_long_query_beyond_url_limit(db):
    query = "type:Organization or(" + ",".join(f'name:"Acme Widgets {i}"' for i in range(600)) + ")"
    assert len(query) > 8192
    result = db.dql(query, size=0)
    assert "hits" in result


def test_live_entities(db):
    result = db.entities("Diffbot is a company based in Menlo Park.")
    assert "entities" in result


def _redacted(account) -> str:
    """Account bodies carry ``token``/``childTokens``: only ever show the other keys."""
    return f"keys={sorted(k for k in account if k not in ('token', 'childTokens'))}"


def test_live_account_and_verify_token(db):
    account = db.account(days=1)
    assert isinstance(account, dict), _redacted({})
    assert "plan" in account or "name" in account or "usage" in account, _redacted(account)
    assert db.verify_token() is True


def test_live_verify_token_rejects_a_bad_token():
    from diffbot import Diffbot

    assert Diffbot(token="not-a-real-token").verify_token() is False


def test_live_extract_with_fields_and_timeout(db):
    result = db.extract("https://example.com", "article", fmt="json", fields=["links"], timeout=45000)
    assert "objects" in result and len(result["objects"]) > 0


CRAWL_PREFIX = "sdk-live-"


def _purge_leaked_crawls(db) -> None:
    cutoff = time.time() - 3600
    for job in db.crawl_list_jobs():
        name = job.get("name", "")
        if name.startswith(CRAWL_PREFIX):
            try:
                created = int(name.rsplit("-", 1)[-1])
            except ValueError:
                continue
            if created < cutoff:
                db.crawl_delete_job(name)


def test_live_crawl_start_poll_download(db):
    _purge_leaked_crawls(db)
    name = f"{CRAWL_PREFIX}{uuid.uuid4().hex[:8]}-{int(time.time())}"  # 28 chars; API limit is 30
    try:
        for _ in db.crawl("https://example.com", job_name=name, hops=0, max_to_crawl=5, max_to_process=5):
            pass
        deadline = time.time() + 180
        while time.time() < deadline:
            if db.crawl_get_job(name).get("jobStatus", {}).get("status", 0) not in (0, 7):
                break
            time.sleep(5)
        records = db.crawl_download(name)
        assert isinstance(records, list)
        assert isinstance(db.crawl_download(name, format="csv"), str)
    finally:
        db.crawl_delete_job(name)
