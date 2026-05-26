import os
import pathlib

import click

from diffbot import Diffbot

CREDENTIALS_PATH = pathlib.Path.home() / ".diffbot" / "credentials"


def resolve_token() -> str:
    """Return the Diffbot API token from the env var, falling back to ~/.diffbot/credentials."""
    token = os.environ.get("DIFFBOT_API_TOKEN", "").strip()
    if token:
        return token

    if CREDENTIALS_PATH.exists():
        for line in CREDENTIALS_PATH.read_text().splitlines():
            line = line.strip()
            if line.startswith("DIFFBOT_API_TOKEN="):
                return line[len("DIFFBOT_API_TOKEN="):].strip()

    return ""


def get_client() -> Diffbot:
    token = resolve_token()
    if not token:
        click.echo(
            "Error: no Diffbot API token found.\n"
            "  Set a DIFFBOT_API_TOKEN environment variable, or\n"
            f"  write 'DIFFBOT_API_TOKEN=YOUR_TOKEN' to {CREDENTIALS_PATH}",
            err=True,
        )
        raise click.Abort()
    return Diffbot(token=token)
