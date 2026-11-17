"""Diffbot NLP API: entity identification, resolution, and sentiment."""

from typing import TYPE_CHECKING, Any, Dict

from ._constants import NLP_HOST_BASE
from .types import EntitiesResponse

if TYPE_CHECKING:
    from .client import Diffbot, DiffbotAsync

NLP_BASE = f"{NLP_HOST_BASE}/v1/"
NLP_FIELDS = "entities,sentiment"


def entities(
    client: "Diffbot",
    text: str,
    *,
    lang: str = "auto",
) -> EntitiesResponse:
    params: Dict[str, Any] = {"token": client.token, "fields": NLP_FIELDS}
    payload = [{"lang": lang, "format": "plain text", "content": text}]
    response = client.request("POST", client.nlp_url, params=params, json=payload)
    data = response.json()
    return data[0] if isinstance(data, list) else data


async def entities_async(
    client: "DiffbotAsync",
    text: str,
    *,
    lang: str = "auto",
) -> EntitiesResponse:
    params: Dict[str, Any] = {"token": client.token, "fields": NLP_FIELDS}
    payload = [{"lang": lang, "format": "plain text", "content": text}]
    response = await client.request("POST", client.nlp_url, params=params, json=payload)
    data = response.json()
    return data[0] if isinstance(data, list) else data
