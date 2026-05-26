"""Diffbot NLP API: entity identification, resolution, and sentiment."""

from typing import TYPE_CHECKING, Any, Dict

if TYPE_CHECKING:
    from .client import Diffbot, DiffbotAsync

NLP_BASE = "https://nl.diffbot.com/v1/"
NLP_FIELDS = "entities,sentiment"


def entities(
    client: "Diffbot",
    text: str,
    *,
    lang: str = "auto",
) -> Dict[str, Any]:
    params = {"token": client.token, "fields": NLP_FIELDS}
    payload = [{"lang": lang, "format": "plain text", "content": text}]
    response = client._http.post(client.nlp_url, params=params, json=payload)
    client._raise_for_status(response)
    data = response.json()
    return data[0] if isinstance(data, list) else data


async def entities_async(
    client: "DiffbotAsync",
    text: str,
    *,
    lang: str = "auto",
) -> Dict[str, Any]:
    params = {"token": client.token, "fields": NLP_FIELDS}
    payload = [{"lang": lang, "format": "plain text", "content": text}]
    response = await client._http.post(client.nlp_url, params=params, json=payload)
    client._raise_for_status(response)
    data = response.json()
    return data[0] if isinstance(data, list) else data
