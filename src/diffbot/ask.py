"""Diffbot LLM RAG API: stream a chat completion."""

import json
from typing import TYPE_CHECKING, Any, AsyncIterator, Dict, Iterator, List

if TYPE_CHECKING:
    from .client import Diffbot, DiffbotAsync


def _build_payload(client: Any, messages: List[Dict[str, str]]) -> tuple:
    headers = {"Authorization": f"Bearer {client.token}"}
    payload = {"model": "diffbot-small-xl", "messages": messages, "stream": True}
    return headers, payload


def _parse_chunk(line: str):
    try:
        chunk = json.loads(line.replace("data: ", ""))
    except json.JSONDecodeError:
        return None
    choices = chunk.get("choices")
    if choices and choices[0].get("delta", {}).get("content"):
        return choices[0]["delta"]["content"]
    return None


def ask(client: "Diffbot", messages: List[Dict[str, str]]) -> Iterator[str]:
    headers = {"Authorization": f"Bearer {client.token}"}
    payload = {"model": "diffbot-small-xl", "messages": messages, "stream": True}
    with client._http.stream("POST", client.llm_url, headers=headers, json=payload) as response:
        client._raise_for_status(response)
        for line in response.iter_lines():
            if line:
                content = _parse_chunk(line)
                if content:
                    yield content


async def ask_async(client: "DiffbotAsync", messages: List[Dict[str, str]]) -> AsyncIterator[str]:
    headers = {"Authorization": f"Bearer {client.token}"}
    payload = {"model": "diffbot-small-xl", "messages": messages, "stream": True}
    async with client._http.stream("POST", client.llm_url, headers=headers, json=payload) as response:
        client._raise_for_status(response)
        async for line in response.aiter_lines():
            if line:
                content = _parse_chunk(line)
                if content:
                    yield content
