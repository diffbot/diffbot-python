"""Cheap live checks against the real API (``pytest -m live``).

Skipped by default. Assertions are on response *shape* only, never web content.
Never include token values in assertion messages.
"""
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
    body = db.dql('type:Organization name:"Diffbot"', size=1, format="csv", raw=True)
    assert isinstance(body, bytes) and len(body) > 0


def test_live_dql_post_jsonl(db):
    body = db.dql('type:Organization name:"Diffbot"', size=1, format="jsonl", raw=True)
    assert isinstance(body, bytes) and len(body) > 0


def test_live_dql_long_query_beyond_url_limit(db):
    query = "type:Organization or(" + ",".join(f'name:"Acme Widgets {i}"' for i in range(600)) + ")"
    assert len(query) > 8192
    result = db.dql(query, size=0)
    assert "hits" in result


def test_live_entities(db):
    result = db.entities("Diffbot is a company based in Menlo Park.")
    assert "entities" in result
