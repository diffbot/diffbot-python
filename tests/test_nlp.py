import json

import httpx
import pytest

from diffbot import Diffbot, DiffbotAsync

DOC = [{"entities": [], "sentiment": 0.1, "summary": "s"}]


def _capture():
    seen = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return httpx.Response(200, json=DOC)

    return seen, handler


def test_nlp_defaults_omit_fields_and_unwraps_list():
    seen, handler = _capture()
    db = Diffbot(token="tok", transport=httpx.MockTransport(handler))
    assert db.nlp("hello") == DOC[0]
    (req,) = seen
    assert req.method == "POST"
    assert str(req.url).startswith("https://nl.diffbot.com/v1/")
    assert dict(req.url.params) == {"token": "tok"}
    assert json.loads(req.content) == [{"lang": "auto", "format": "plain text", "content": "hello"}]


def test_nlp_options_shape_request():
    seen, handler = _capture()
    db = Diffbot(token="tok", transport=httpx.MockTransport(handler))
    db.nlp("t", fields=["summary", "facts"], lang="en", document_type="blog",
           custom_summary={"max_number_of_sentences": 2})
    (req,) = seen
    assert req.url.params["fields"] == "summary,facts"
    assert json.loads(req.content) == [{
        "lang": "en", "format": "plain text", "content": "t", "documentType": "blog",
        "customSummary": {"maxNumberOfSentences": 2},
    }]


def test_entities_unchanged_still_hardcodes_fields():
    seen, handler = _capture()
    db = Diffbot(token="tok", transport=httpx.MockTransport(handler))
    db.entities("x")
    assert seen[0].url.params["fields"] == "entities,sentiment"
    assert json.loads(seen[0].content) == [{"lang": "auto", "format": "plain text", "content": "x"}]


@pytest.mark.anyio
async def test_async_nlp_options_shape_request():
    seen, handler = _capture()
    db = DiffbotAsync(token="tok", transport=httpx.MockTransport(handler))
    assert await db.nlp("t") == DOC[0]
    await db.nlp("Title\n\nBody", fields=["language"], format="plain text with title",
                 custom_summary={"max_number_of_sentences": 3})
    assert "fields" not in seen[0].url.params
    assert seen[1].url.params["fields"] == "language"
    assert json.loads(seen[1].content) == [{
        "lang": "auto", "format": "plain text with title", "content": "Title\n\nBody",
        "customSummary": {"maxNumberOfSentences": 3},
    }]
    seen.clear()
    await db.entities("x")
    assert seen[0].url.params["fields"] == "entities,sentiment"
