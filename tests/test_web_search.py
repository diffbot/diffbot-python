import pytest


"""
Live
"""

@pytest.mark.live
def test_live_web_search(db):
    result = db.web_search("diffbot knowledge graph", num_results=3)
    assert "search_results" in result
    assert len(result["search_results"]) > 0


@pytest.mark.live
def test_live_web_search_snippet_length(db):
    long = db.web_search("diffbot knowledge graph", num_results=3)
    short = db.web_search("diffbot knowledge graph", num_results=3, snippet_length="short")
    assert len(short["search_results"]) > 0
    total_long = sum(len(r.get("content", "")) for r in long["search_results"])
    total_short = sum(len(r.get("content", "")) for r in short["search_results"])
    assert total_short <= total_long


"""
Mocked
"""

def test_web_search_sends_snippet_length_param():
    import httpx
    from diffbot import Diffbot

    seen = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen.update(request.url.params)
        return httpx.Response(200, json={"search_results": []})

    db = Diffbot(token="t", transport=httpx.MockTransport(handler))
    db.web_search("q", num_results=3, snippet_length="short")
    assert seen["size"] == "3"
    assert seen["snippetLength"] == "SHORT"

    seen.clear()
    db.web_search("q")
    assert "snippetLength" not in seen

    seen.clear()
    db.web_search("url:https://example.com", snippet_length="full")
    assert seen["snippetLength"] == "FULL"
    assert seen["rerank"] == "none"
