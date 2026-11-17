"""Diffbot Knowledge Graph APIs: DQL search and entity enhancement."""

import asyncio
import pathlib
from concurrent.futures import ThreadPoolExecutor
from typing import TYPE_CHECKING, Any, Dict, List, Mapping, Optional, Sequence, Union

from ._constants import KG_BASE
from .ontology import Ontology
from .types import ExportFormat

if TYPE_CHECKING:
    from .client import Diffbot, DiffbotAsync

KG_DQL_ENDPOINT = f"{KG_BASE}/kg/v3/dql"
KG_ONTOLOGY_ENDPOINT = f"{KG_BASE}/kg/ontology"


def _build_dql_body(
    query: str,
    size: int,
    from_: int,
    format: ExportFormat,
    filter: Optional[str],
    exportspec: Optional[str],
    extra: Optional[Mapping[str, Any]],
) -> Dict[str, Any]:
    """JSON body for ``POST /kg/v3/dql`` (``DqlPostRequest``). The token is *not* part
    of the body; it travels in the query string, as the spec's security scheme says."""
    body: Dict[str, Any] = {"query": query, "size": size}
    if from_:
        body["from"] = from_
    if format != "json":
        body["format"] = format
    if filter is not None:
        body["filter"] = filter
    if exportspec is not None:
        body["exportspec"] = exportspec
    if extra:
        body.update(extra)
    return body


def dql(
    client: "Diffbot",
    query: str,
    *,
    size: int = 10,
    from_: int = 0,
    format: ExportFormat = "json",
    filter: Optional[str] = None,
    exportspec: Optional[str] = None,
    extra: Optional[Mapping[str, Any]] = None,
    raw: bool = False,
) -> Union[Dict[str, Any], bytes]:
    body = _build_dql_body(query, size, from_, format, filter, exportspec, extra)
    response = client.request("POST", client.dql_url, params={"token": client.token}, json=body)
    return response.content if raw else response.json()


async def dql_async(
    client: "DiffbotAsync",
    query: str,
    *,
    size: int = 10,
    from_: int = 0,
    format: ExportFormat = "json",
    filter: Optional[str] = None,
    exportspec: Optional[str] = None,
    extra: Optional[Mapping[str, Any]] = None,
    raw: bool = False,
) -> Union[Dict[str, Any], bytes]:
    body = _build_dql_body(query, size, from_, format, filter, exportspec, extra)
    response = await client.request("POST", client.dql_url, params={"token": client.token}, json=body)
    return response.content if raw else response.json()


def dql_parallel(
    client: "Diffbot",
    queries: Sequence[Dict[str, Any]],
    *,
    workers: int = 8,
) -> List[Union[Dict[str, Any], bytes]]:
    if not queries:
        return []
    with ThreadPoolExecutor(max_workers=min(workers, len(queries))) as ex:
        return list(ex.map(lambda q: dql(client, **q), queries))


async def dql_parallel_async(
    client: "DiffbotAsync",
    queries: Sequence[Dict[str, Any]],
    *,
    workers: int = 8,
) -> List[Union[Dict[str, Any], bytes]]:
    if not queries:
        return []
    sem = asyncio.Semaphore(workers)

    async def _one(q: Dict[str, Any]) -> Union[Dict[str, Any], bytes]:
        async with sem:
            return await dql_async(client, **q)

    return await asyncio.gather(*(_one(q) for q in queries))


def dql_refresh_ontology(client: "Diffbot", dest: pathlib.Path) -> None:
    response = client.request("GET", client.ontology_url)
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_bytes(response.content)


def dql_fetch_ontology(client: "Diffbot") -> Ontology:
    """Download the ontology and return it as a queryable :class:`Ontology`.

    Performs no caching — the caller decides whether and where to hold onto the
    result. Use :func:`dql_refresh_ontology` instead to persist raw bytes to disk.
    """
    response = client.request("GET", client.ontology_url)
    return Ontology.from_json(response.content)


async def dql_fetch_ontology_async(client: "DiffbotAsync") -> Ontology:
    """Async variant of :func:`dql_fetch_ontology`."""
    response = await client.request("GET", client.ontology_url)
    return Ontology.from_json(response.content)
