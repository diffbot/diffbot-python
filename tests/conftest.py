import os

import pytest

from diffbot import Diffbot


@pytest.fixture(scope="session")
def live_token():
    token = os.environ.get("DIFFBOT_TOKEN")
    if not token:
        pytest.skip("DIFFBOT_TOKEN not set")
    return token


@pytest.fixture(scope="session")
def db(live_token):
    return Diffbot(token=live_token)
