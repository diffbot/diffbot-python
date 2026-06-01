"""In-memory navigation of the Diffbot Knowledge Graph ontology.

The ontology is a JSON document describing the Knowledge Graph's entity types,
composite types, enums, and taxonomies. An agent constructing DQL needs it to
look up real field paths and taxonomy values instead of guessing them.

This module is pure and storage-agnostic: build an :class:`Ontology` from
already-parsed data (or from raw JSON / a file path) and query it. How the
ontology document is fetched, and whether or where it is cached, is left
entirely to the caller — the `db` CLI caches it on disk at
``~/.diffbot/ontology.json``; an in-process consumer (e.g. langchain) can cache
the :class:`Ontology` in memory. Fetch a fresh one over HTTP with
:meth:`diffbot.Diffbot.dql_fetch_ontology`.
"""

import json
import pathlib
import re
from typing import Any, Dict, List, Optional, Tuple, Union


class Ontology:
    """Queryable view over a parsed Diffbot ontology document.

    The instance holds the parsed document on :attr:`data` and exposes pure
    lookup methods over it. Nothing here performs I/O — construct with already
    parsed data, or use :meth:`from_json` / :meth:`from_path` for convenience.
    """

    def __init__(self, data: Dict[str, Any]):
        self.data = data

    @classmethod
    def from_json(cls, raw: Union[str, bytes]) -> "Ontology":
        """Build from a raw JSON string or bytes (e.g. an HTTP response body)."""
        return cls(json.loads(raw))

    @classmethod
    def from_path(cls, path: Union[str, pathlib.Path]) -> "Ontology":
        """Build from a JSON file on disk."""
        return cls(json.loads(pathlib.Path(path).read_text()))

    def types(self) -> List[str]:
        """All entity type names (e.g. ``Organization``, ``Person``)."""
        return sorted(self.data.get("types", {}).keys())

    def composites(self) -> List[str]:
        """All composite type names (e.g. ``Location``, ``Employment``)."""
        return sorted(self.data.get("composites", {}).keys())

    def enums(self) -> List[str]:
        """All enum type names (e.g. ``Language``, ``Gender``)."""
        return sorted(self.data.get("enums", {}).keys())

    def taxonomies(self) -> List[str]:
        """All taxonomy names (e.g. ``OrganizationCategory``)."""
        return sorted(self.data.get("taxonomies", {}).keys())

    @staticmethod
    def _fields_of(container: Dict[str, Any], type_name: str) -> Dict[str, Any]:
        entry = container.get(type_name)
        if entry is None:
            raise KeyError(f"Unknown name: {type_name}")
        return entry.get("fields", {})

    def fields_for(self, type_name: str) -> Dict[str, Any]:
        """Return the field map of an entity type or composite.

        Auto-routes: ``type_name`` may be an entity type (``Organization``) or a
        composite (``Location``). Raises ``KeyError`` if it is neither.
        """
        types = self.data.get("types", {})
        composites = self.data.get("composites", {})
        if type_name in types:
            return self._fields_of(types, type_name)
        if type_name in composites:
            return self._fields_of(composites, type_name)
        raise KeyError(f"{type_name} is not a known entity type or composite")

    @staticmethod
    def filter_fields(
        fields: Dict[str, Any],
        search: Optional[str],
        include_deprecated: bool = False,
    ) -> List[Tuple[str, Dict[str, Any]]]:
        """Filter a field map by a name regex, dropping deprecated by default."""
        pattern = re.compile(search, re.IGNORECASE) if search else None
        out = []
        for name, meta in fields.items():
            if not include_deprecated and meta.get("isDeprecated"):
                continue
            if pattern and not pattern.search(name):
                continue
            out.append((name, meta))
        return out

    def taxonomy_values(self, name: str, search: Optional[str] = None) -> List[str]:
        """Flatten a taxonomy's values (recursing into children), optionally filtered."""
        tax = self.data.get("taxonomies", {}).get(name)
        if tax is None:
            raise KeyError(f"Unknown taxonomy: {name}")
        pattern = re.compile(search, re.IGNORECASE) if search else None
        out: List[str] = []

        def walk(node: Dict[str, Any]) -> None:
            n = node.get("name")
            if n and (pattern is None or pattern.search(n)):
                out.append(n)
            for child in node.get("children", []) or []:
                walk(child)

        for cat in tax.get("categories", []) or []:
            walk(cat)
        return out

    def enum_values(self, name: str) -> List[str]:
        """Return the allowed values of an enum."""
        enum = self.data.get("enums", {}).get(name)
        if enum is None:
            raise KeyError(f"Unknown enum: {name}")
        return list(enum.get("values", []))

    def find_named(self, search: str) -> List[str]:
        """Fallback search: every ``name`` anywhere in the document matching a regex."""
        pattern = re.compile(search, re.IGNORECASE)
        found = set()

        def walk(node: Any) -> None:
            if isinstance(node, dict):
                n = node.get("name")
                if isinstance(n, str) and pattern.search(n):
                    found.add(n)
                for v in node.values():
                    walk(v)
            elif isinstance(node, list):
                for v in node:
                    walk(v)

        walk(self.data)
        return sorted(found)

    @staticmethod
    def format_field(name: str, meta: Dict[str, Any]) -> str:
        """Render one field as ``<name>: [<type>] [flags...]`` for display."""
        t = meta.get("type", "?")
        if t == "LinkedEntity":
            le = meta.get("leType") or []
            if le:
                t = f"LinkedEntity ({le[0]})"
        flags = []
        if meta.get("isList"):
            flags.append("isList")
        if meta.get("isComposite"):
            flags.append("isComposite")
        if meta.get("isEnum"):
            flags.append("isEnum")
        if meta.get("isDeprecated"):
            flags.append("DEPRECATED")
        suffix = "".join(f" [{f}]" for f in flags)
        return f"{name}: [{t}]{suffix}"
