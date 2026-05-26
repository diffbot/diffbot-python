"""
diffbot - Python client library for the Diffbot APIs.
"""

__version__ = "0.1.0"

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

__all__ = [
    "Diffbot",
    "DiffbotAsync",
    "CrawlEvent",
    "CrawlEventType",
    "DiffbotError",
    "AuthError",
    "ExtractionError",
    "RateLimitError",
    "APIError",
    "ValidationError",
]
