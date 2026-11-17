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


"""
Multi-value text and snippet_length validation (S2)
"""

import httpx  # noqa: E402

from diffbot import Diffbot, DiffbotAsync, ValidationError  # noqa: E402


def _cap():
    seen = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return httpx.Response(200, json={"search_results": []})

    return seen, handler


@pytest.mark.parametrize("n", [1, 2, 5])
def test_web_search_text_sequence_sends_repeated_params(n):
    seen, handler = _cap()
    db = Diffbot(token="t", transport=httpx.MockTransport(handler))
    texts = [f"q{i}" for i in range(n)]
    db.web_search(texts)
    (req,) = seen
    assert req.method == "GET"
    assert req.url.params.get_list("text") == texts
    assert req.headers["authorization"] == "Bearer t"


def test_web_search_single_string_unchanged():
    seen, handler = _cap()
    db = Diffbot(token="t", transport=httpx.MockTransport(handler))
    db.web_search("one query", num_results=1)
    assert seen[0].url.params.get_list("text") == ["one query"]
    assert seen[0].url.params["size"] == "1"


@pytest.mark.parametrize("texts", [[], [f"q{i}" for i in range(6)]])
def test_web_search_text_out_of_range_raises(texts):
    seen, handler = _cap()
    db = Diffbot(token="t", transport=httpx.MockTransport(handler))
    with pytest.raises(ValidationError, match="1-5"):
        db.web_search(texts)
    assert seen == []


def test_web_search_snippet_length_case_normalized_and_validated():
    seen, handler = _cap()
    db = Diffbot(token="t", transport=httpx.MockTransport(handler))
    db.web_search("q", snippet_length="Medium")  # type: ignore[arg-type]
    assert seen[0].url.params["snippetLength"] == "MEDIUM"
    with pytest.raises(ValidationError, match="snippet_length"):
        db.web_search("q", snippet_length="huge")  # type: ignore[arg-type]
    assert len(seen) == 1


@pytest.mark.anyio
async def test_async_web_search_multi_text_and_validation():
    seen, handler = _cap()
    db = DiffbotAsync(token="t", transport=httpx.MockTransport(handler))
    await db.web_search(["a", "b"], snippet_length="full")
    assert seen[0].url.params.get_list("text") == ["a", "b"]
    assert seen[0].url.params["snippetLength"] == "FULL"
    assert seen[0].url.params["rerank"] == "none"
    await db.web_search("solo")
    assert seen[1].url.params.get_list("text") == ["solo"]
    with pytest.raises(ValidationError):
        await db.web_search([])
    with pytest.raises(ValidationError):
        await db.web_search(["x"] * 6)
    with pytest.raises(ValidationError, match="snippet_length"):
        await db.web_search("q", snippet_length="nope")  # type: ignore[arg-type]
    assert len(seen) == 2
