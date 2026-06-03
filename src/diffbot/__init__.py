"""
diffbot - Python client library for the Diffbot APIs.
"""

from importlib.metadata import PackageNotFoundError, version as _version

try:
    __version__ = _version("diffbot-python")
except PackageNotFoundError:  # not installed (e.g. running from a source tree)
    __version__ = "0.0.0"

from ._auth import resolve_token
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
