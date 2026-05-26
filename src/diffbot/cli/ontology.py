import json
import pathlib
import re
from typing import Any, Dict, List, Optional

ONTOLOGY_PATH = pathlib.Path.home() / ".diffbot" / "ontology.json"

_CACHE: Dict[str, Any] = {}


def load() -> Dict[str, Any]:
    if "data" not in _CACHE:
        if not ONTOLOGY_PATH.exists():
            raise FileNotFoundError(
                f"Ontology not found at {ONTOLOGY_PATH}. Run: db dql init"
            )
        _CACHE["data"] = json.loads(ONTOLOGY_PATH.read_text())
    return _CACHE["data"]


def list_types() -> List[str]:
    return sorted(load().get("types", {}).keys())


def list_composites() -> List[str]:
    return sorted(load().get("composites", {}).keys())


def list_enums() -> List[str]:
    return sorted(load().get("enums", {}).keys())


def list_taxonomies() -> List[str]:
    return sorted(load().get("taxonomies", {}).keys())


def _fields_of(container: Dict[str, Any], type_name: str) -> Dict[str, Any]:
    entry = container.get(type_name)
    if entry is None:
        raise KeyError(f"Unknown name: {type_name}")
    return entry.get("fields", {})


def fields_for(type_name: str) -> Dict[str, Any]:
    data = load()
    types = data.get("types", {})
    composites = data.get("composites", {})
    if type_name in types:
        return _fields_of(types, type_name)
    if type_name in composites:
        return _fields_of(composites, type_name)
    raise KeyError(f"{type_name} is not a known entity type or composite")


def format_field(name: str, meta: Dict[str, Any]) -> str:
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


def filter_fields(fields: Dict[str, Any], search: Optional[str], include_deprecated: bool = False) -> List[tuple]:
    pattern = re.compile(search, re.IGNORECASE) if search else None
    out = []
    for name, meta in fields.items():
        if not include_deprecated and meta.get("isDeprecated"):
            continue
        if pattern and not pattern.search(name):
            continue
        out.append((name, meta))
    return out


def taxonomy_values(name: str, search: Optional[str] = None) -> List[str]:
    data = load()
    tax = data.get("taxonomies", {}).get(name)
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


def enum_values(name: str) -> List[str]:
    data = load()
    enum = data.get("enums", {}).get(name)
    if enum is None:
        raise KeyError(f"Unknown enum: {name}")
    return list(enum.get("values", []))


def find_named(search: str) -> List[str]:
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

    walk(load())
    return sorted(found)
