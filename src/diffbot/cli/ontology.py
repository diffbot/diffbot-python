"""CLI-side ontology access: a disk cache over the storage-agnostic core.

The navigation logic lives in :mod:`diffbot.ontology` (the `Ontology` class).
This module adds the CLI's caching policy on top: the ontology is read once from
``~/.diffbot/ontology.json`` (populated by `db dql init`) and held in
``_CACHE``. The module-level functions preserve the historical CLI surface and
simply delegate to an `Ontology` built from the cached document.
"""

import json
import pathlib
from typing import Any, Dict, List, Optional, Tuple

from diffbot.ontology import Ontology

ONTOLOGY_PATH = pathlib.Path.home() / ".diffbot" / "ontology.json"

_CACHE: Dict[str, Any] = {}


def _data() -> Dict[str, Any]:
    if "data" not in _CACHE:
        if not ONTOLOGY_PATH.exists():
            raise FileNotFoundError(
                f"Ontology not found at {ONTOLOGY_PATH}. Run: db dql init"
            )
        _CACHE["data"] = json.loads(ONTOLOGY_PATH.read_text())
    return _CACHE["data"]


def _ontology() -> Ontology:
    return Ontology(_data())


def list_types() -> List[str]:
    return _ontology().types()


def list_composites() -> List[str]:
    return _ontology().composites()


def list_enums() -> List[str]:
    return _ontology().enums()


def list_taxonomies() -> List[str]:
    return _ontology().taxonomies()


def fields_for(type_name: str) -> Dict[str, Any]:
    return _ontology().fields_for(type_name)


def format_field(name: str, meta: Dict[str, Any]) -> str:
    return Ontology.format_field(name, meta)


def filter_fields(
    fields: Dict[str, Any], search: Optional[str], include_deprecated: bool = False
) -> List[Tuple[str, Dict[str, Any]]]:
    return Ontology.filter_fields(fields, search, include_deprecated=include_deprecated)


def taxonomy_values(name: str, search: Optional[str] = None) -> List[str]:
    return _ontology().taxonomy_values(name, search)


def enum_values(name: str) -> List[str]:
    return _ontology().enum_values(name)


def find_named(search: str) -> List[str]:
    return _ontology().find_named(search)
