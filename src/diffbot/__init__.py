"""
diffbot - Python client library for the Diffbot APIs.
"""

__version__ = "0.1.0"

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
