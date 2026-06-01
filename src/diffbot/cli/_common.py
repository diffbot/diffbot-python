import click

from diffbot import Diffbot, resolve_token
from diffbot._auth import CREDENTIALS_PATH, TOKEN_ENV_VAR


def get_client() -> Diffbot:
    """Build a Diffbot client using the shared credential resolution chain.

    Looks at the DIFFBOT_API_TOKEN env var, then ~/.diffbot/credentials.
    """
    token = resolve_token()
    if not token:
        click.echo(
            "Error: no Diffbot API token found.\n"
            f"  Set a {TOKEN_ENV_VAR} environment variable, or\n"
            f"  write '{TOKEN_ENV_VAR}=YOUR_TOKEN' to {CREDENTIALS_PATH}",
            err=True,
        )
        raise click.Abort()
    return Diffbot(token=token)
