import pytest

from diffbot import Diffbot, resolve_token


@pytest.fixture(scope="session")
def live_token():
    token = resolve_token()
    if not token:
        pytest.skip("no Diffbot token found (set DIFFBOT_API_TOKEN or ~/.diffbot/credentials)")
    return token


@pytest.fixture(scope="session")
def db(live_token):
    return Diffbot(token=live_token)
