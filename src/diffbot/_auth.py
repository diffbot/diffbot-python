"""Shared Diffbot credential resolution for both the library and the CLI.

The same lookup chain is used everywhere so a single credential works for the
``db`` CLI and any Python script that constructs a client:

1. An explicit token passed to the client / function.
2. The ``DIFFBOT_API_TOKEN`` environment variable.
3. A ``DIFFBOT_API_TOKEN=...`` line in ``~/.diffbot/credentials``.
"""

import os
import pathlib
from typing import Optional

TOKEN_ENV_VAR = "DIFFBOT_API_TOKEN"
CREDENTIALS_PATH = pathlib.Path.home() / ".diffbot" / "credentials"


def _read_credentials_file() -> str:
    if not CREDENTIALS_PATH.exists():
        return ""
    for line in CREDENTIALS_PATH.read_text().splitlines():
        line = line.strip()
        if line.startswith(f"{TOKEN_ENV_VAR}="):
            return line[len(TOKEN_ENV_VAR) + 1:].strip()
    return ""


def resolve_token(token: Optional[str] = None) -> str:
    """Resolve a Diffbot API token from the explicit argument, env var, or file.

    Returns an empty string if no token can be found.
    """
    if token and token.strip():
        return token.strip()

    env_token = os.environ.get(TOKEN_ENV_VAR, "").strip()
    if env_token:
        return env_token

    return _read_credentials_file()
