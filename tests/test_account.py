import httpx
import pytest

from diffbot import APIError, AuthError, Diffbot, DiffbotAsync

ACCOUNT = {"name": "Acme", "plan": "plus", "usage": [{"date": "2026-11-16", "credits": 3}]}


def make(handler, **kw) -> Diffbot:
    return Diffbot(token="tok", transport=httpx.MockTransport(handler), retry=False, **kw)


def test_account_sends_get_v4_with_days():
    seen = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return httpx.Response(200, json=ACCOUNT)

    assert make(handler).account(days=7) == ACCOUNT
    (req,) = seen
    assert req.method == "GET"
    assert str(req.url).startswith("https://api.diffbot.com/v4/account?")
    assert req.url.params["token"] == "tok"
    assert req.url.params["days"] == "7"


def test_account_omits_days_by_default():
    def handler(request: httpx.Request) -> httpx.Response:
        assert "days" not in request.url.params
        return httpx.Response(200, json=ACCOUNT)

    make(handler).account()


def test_account_honors_api_base():
    def handler(request: httpx.Request) -> httpx.Response:
        assert str(request.url).startswith("http://localhost:9/v4/account")
        return httpx.Response(200, json={})

    make(handler, api_base="http://localhost:9").account()


def test_verify_token_true_uses_days_1():
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.params["days"] == "1"
        return httpx.Response(200, json=ACCOUNT)

    assert make(handler).verify_token() is True


@pytest.mark.parametrize("status", [401, 403])
def test_verify_token_false_on_auth_error(status):
    db = make(lambda r: httpx.Response(status, json={"errorCode": status, "error": "bad token"}))
    assert db.verify_token() is False
    with pytest.raises(AuthError):
        db.account()


@pytest.mark.parametrize("status", [429, 500, 404])
def test_verify_token_propagates_other_errors(status):
    db = make(lambda r: httpx.Response(status, text="nope"))
    with pytest.raises(APIError):
        db.verify_token()


def test_verify_token_propagates_network_errors():
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("down")

    with pytest.raises(httpx.ConnectError):
        make(handler).verify_token()


@pytest.mark.anyio
async def test_async_account_and_verify_token():
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.method == "GET" and request.url.params["days"] == "1"
        return httpx.Response(200, json=ACCOUNT)

    db = DiffbotAsync(token="tok", transport=httpx.MockTransport(handler))
    assert await db.account(days=1) == ACCOUNT
    assert await db.verify_token() is True


@pytest.mark.anyio
async def test_async_verify_token_false_and_propagation():
    bad = DiffbotAsync(token="tok", transport=httpx.MockTransport(lambda r: httpx.Response(401, text="no")), retry=False)
    assert await bad.verify_token() is False
    boom = DiffbotAsync(token="tok", transport=httpx.MockTransport(lambda r: httpx.Response(500, text="x")), retry=False)
    with pytest.raises(APIError):
        await boom.verify_token()
