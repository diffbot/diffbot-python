"""Diffbot Knowledge Graph APIs: DQL search and entity enhancement."""

import pathlib
from concurrent.futures import ThreadPoolExecutor
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Sequence, Union

if TYPE_CHECKING:
    from .client import Diffbot, DiffbotAsync

KG_DQL_ENDPOINT = "https://kg.diffbot.com/kg/v3/dql"
KG_ONTOLOGY_ENDPOINT = "https://kg.diffbot.com/kg/ontology"


def _build_dql_params(
    client: Any,
    query: str,
    size: int,
    from_: int,
    format: str,
    filter: Optional[str],
    exportspec: Optional[str],
    extra: Optional[Dict[str, str]],
) -> Dict[str, Any]:
    params: Dict[str, Any] = {"token": client.token, "query": query, "size": size}
    if from_:
        params["from"] = from_
    if format != "json":
        params["format"] = format
    if filter is not None:
        params["filter"] = filter
    if exportspec is not None:
        params["exportspec"] = exportspec
    if extra:
        params.update(extra)
    return params


def dql(
    client: "Diffbot",
    query: str,
    *,
    size: int = 10,
    from_: int = 0,
    format: str = "json",
    filter: Optional[str] = None,
    exportspec: Optional[str] = None,
    extra: Optional[Dict[str, str]] = None,
    raw: bool = False,
) -> Union[Dict[str, Any], bytes]:
    params = _build_dql_params(client, query, size, from_, format, filter, exportspec, extra)
    response = client._http.get(KG_DQL_ENDPOINT, params=params)
    client._raise_for_status(response)
    return response.content if raw else response.json()


async def dql_async(
    client: "DiffbotAsync",
    query: str,
    *,
    size: int = 10,
    from_: int = 0,
    format: str = "json",
    filter: Optional[str] = None,
    exportspec: Optional[str] = None,
    extra: Optional[Dict[str, str]] = None,
    raw: bool = False,
) -> Union[Dict[str, Any], bytes]:
    params = _build_dql_params(client, query, size, from_, format, filter, exportspec, extra)
    response = await client._http.get(KG_DQL_ENDPOINT, params=params)
    client._raise_for_status(response)
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


def dql_refresh_ontology(client: "Diffbot", dest: pathlib.Path) -> None:
    response = client._http.get(KG_ONTOLOGY_ENDPOINT)
    client._raise_for_status(response)
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_bytes(response.content)
