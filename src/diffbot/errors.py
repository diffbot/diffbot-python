"""Exception hierarchy for the Diffbot SDK."""

import json
from typing import Optional


class DiffbotError(Exception):
    """Base class for all Diffbot SDK errors."""


class ValidationError(DiffbotError):
    """Client-side validation failed (e.g. missing token, malformed argument)."""


class APIError(DiffbotError):
    """The Diffbot API returned an error response."""

    def __init__(self, status_code: int, body: str):
        self.status_code = status_code
        self.body = body
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

    def __init__(self, status_code: int, body: str, retry_after: Optional[str] = None):
        super().__init__(status_code, body)
        self.retry_after = retry_after


class ExtractionError(DiffbotError):
    """The Diffbot API returned a 200 but reported an extraction failure."""

    def __init__(self, error_code: int, error: str):
        self.error_code = error_code
        self.error = error
        super().__init__(f"Diffbot extraction error {error_code}: {error}")
