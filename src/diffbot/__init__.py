"""
diffbot - Python client library for the Diffbot APIs.
"""

import warnings as _warnings
from importlib.metadata import PackageNotFoundError, version as _version

def _installed_version(dist: str):
    try:
        return _version(dist)
    except PackageNotFoundError:
        return None


# The distribution was renamed from diffbot-python to diffbot. The final
# diffbot-python release ships this same code (see legacy/diffbot-python), so
# fall back to its version when that's what is installed.
_legacy_version = _installed_version("diffbot-python")
# "0.0.0" when not installed (e.g. running from a source tree).
__version__ = _installed_version("diffbot") or _legacy_version or "0.0.0"

# Both distributions ship this module, so a diffbot-python install (alone, or
# left over next to diffbot) should migrate. FutureWarning, unlike
# DeprecationWarning, is shown by default wherever the import happens.
if _legacy_version is not None:
    _warnings.warn(
        "diffbot-python has been renamed to diffbot and will receive no further "
        "updates. Run `pip uninstall diffbot-python && pip install "
        "--force-reinstall diffbot` and replace diffbot-python with diffbot in "
        "your requirements.",
        FutureWarning,
        stacklevel=2,
    )

from ._auth import resolve_token
from .ask import json_schema_format
from .client import Diffbot, DiffbotAsync
from .crawl import CrawlEvent, CrawlEventType
from .errors import (
    APIError,
    AuthError,
    DiffbotError,
    ExtractionError,
    RateLimitError,
    ValidationError,
)
from .ontology import Ontology

__all__ = [
    "Diffbot",
    "DiffbotAsync",
    "resolve_token",
    "json_schema_format",
    "CrawlEvent",
    "CrawlEventType",
    "Ontology",
    "DiffbotError",
    "AuthError",
    "ExtractionError",
    "RateLimitError",
    "APIError",
    "ValidationError",
]
