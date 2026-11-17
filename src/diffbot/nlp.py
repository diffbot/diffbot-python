"""Diffbot NLP API: entity identification, resolution, and sentiment."""

from typing import TYPE_CHECKING, Any, Dict, Optional, Sequence

from ._constants import NLP_HOST_BASE
from .types import EntitiesResponse, NlpCustomSummary, NlpField, NlpFormat, NlpResponse

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


def _build_nlp_request(
    client: Any,
    text: str,
    fields: Optional[Sequence[NlpField]],
    lang: str,
    format: NlpFormat,
    document_type: Optional[str],
    custom_summary: Optional[NlpCustomSummary],
) -> Any:
    params: Dict[str, Any] = {"token": client.token}
    if fields is not None:
        params["fields"] = fields if isinstance(fields, str) else ",".join(fields)
    document: Dict[str, Any] = {"lang": lang, "format": format, "content": text}
    if document_type is not None:
        document["documentType"] = document_type
    if custom_summary is not None:
        max_sentences = custom_summary.get("max_number_of_sentences")
        if max_sentences is not None:
            document["customSummary"] = {"maxNumberOfSentences": max_sentences}
    return params, [document]


def nlp(
    client: "Diffbot",
    text: str,
    *,
    fields: Optional[Sequence[NlpField]] = None,
    lang: str = "auto",
    format: NlpFormat = "plain text",
    document_type: Optional[str] = None,
    custom_summary: Optional[NlpCustomSummary] = None,
) -> NlpResponse:
    params, payload = _build_nlp_request(client, text, fields, lang, format, document_type, custom_summary)
    response = client.request("POST", client.nlp_url, params=params, json=payload)
    data = response.json()
    return data[0] if isinstance(data, list) else data


async def nlp_async(
    client: "DiffbotAsync",
    text: str,
    *,
    fields: Optional[Sequence[NlpField]] = None,
    lang: str = "auto",
    format: NlpFormat = "plain text",
    document_type: Optional[str] = None,
    custom_summary: Optional[NlpCustomSummary] = None,
) -> NlpResponse:
    params, payload = _build_nlp_request(client, text, fields, lang, format, document_type, custom_summary)
    response = await client.request("POST", client.nlp_url, params=params, json=payload)
    data = response.json()
    return data[0] if isinstance(data, list) else data
