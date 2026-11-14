"""Exception hierarchy for the Diffbot SDK."""

import json
from typing import Dict, Optional


class DiffbotError(Exception):
    """Base class for all Diffbot SDK errors."""


class ValidationError(DiffbotError):
    """Client-side validation failed (e.g. missing token, malformed argument)."""


class APIError(DiffbotError):
    """The Diffbot API returned an error response."""

    def __init__(self, status_code: int, body: str, headers: Optional[Dict[str, str]] = None):
        self.status_code = status_code
        self.body = body
        self.headers = headers
        self.message: Optional[str] = None
        self.request_id: Optional[str] = None
        try:
            data = json.loads(body)
            self.message = data.get("message")
            self.request_id = data.get("requestId")
        except (ValueError, AttributeError):
            pass
        display = self.message or (body[:200] + ("..." if len(body) > 200 else ""))
        super().__init__(f"Diffbot API error {status_code}: {display}")


class AuthError(APIError):
    """Authentication failed (401, 403)."""


class RateLimitError(APIError):
    """Rate limit exceeded (429)."""

    def __init__(
        self,
        status_code: int,
        body: str,
        retry_after: Optional[str] = None,
        headers: Optional[Dict[str, str]] = None,
    ):
        super().__init__(status_code, body, headers=headers)
        self.retry_after = retry_after


class NotFoundError(APIError):
    """A 404 from an endpoint with a documented "not found" shape (e.g. a missing job or report)."""


class JobError(APIError):
    """A job (crawl or bulk) that completed its HTTP request successfully but reports a
    failed status internally.

    Subclasses :class:`APIError` so existing ``except APIError`` sites keep working;
    ``isinstance(err, JobError)`` distinguishes it from a transport-level failure.
    """

    def __init__(self, job_name: str, message: str):
        super().__init__(500, message)
        self.job_name = job_name


class ExtractionError(DiffbotError):
    """The Diffbot API returned a 200 but reported an extraction failure."""

    def __init__(self, error_code: int, error: str):
        self.error_code = error_code
        self.error = error
        super().__init__(f"Diffbot extraction error {error_code}: {error}")
