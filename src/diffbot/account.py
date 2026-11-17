"""Diffbot Account API: usage and token verification (``GET /v4/account``)."""

from typing import TYPE_CHECKING, Any, Dict, Optional

from .errors import AuthError
from .types import AccountResponse

if TYPE_CHECKING:
    from .client import Diffbot, DiffbotAsync


def _params(client: Any, days: Optional[int]) -> Dict[str, Any]:
    params: Dict[str, Any] = {"token": client.token}
    if days is not None:
        params["days"] = days
    return params


def account(client: "Diffbot", days: Optional[int] = None) -> AccountResponse:
    response = client.request("GET", client.account_url, params=_params(client, days))
    return response.json()


async def account_async(client: "DiffbotAsync", days: Optional[int] = None) -> AccountResponse:
    response = await client.request("GET", client.account_url, params=_params(client, days))
    return response.json()


def verify_token(client: "Diffbot") -> bool:
    """``True`` if the token is accepted. Only :class:`AuthError` maps to ``False``;
    every other failure (network, 5xx, rate limit) propagates."""
    try:
        account(client, days=1)
    except AuthError:
        return False
    return True


async def verify_token_async(client: "DiffbotAsync") -> bool:
    try:
        await account_async(client, days=1)
    except AuthError:
        return False
    return True
