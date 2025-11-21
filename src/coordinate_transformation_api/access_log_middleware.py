"""Middleware to capture request metadata for access logging."""

import logging
import threading
import time
from collections.abc import Awaitable, Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

# Thread-local storage for request metadata (survives async context switches)
_request_data = threading.local()


class RequestMetadataFilter(logging.Filter):
    """Logging filter that adds request metadata from thread-local storage."""

    def __init__(
        self: "RequestMetadataFilter", log_forwarded_for: bool = False, client_ip_header: str | None = None
    ) -> None:
        super().__init__()
        self.log_forwarded_for = log_forwarded_for
        self.client_ip_header = client_ip_header

    def filter(self: "RequestMetadataFilter", record: logging.LogRecord) -> bool:
        """Add request metadata to log record."""
        # Get host from thread-local storage
        host = getattr(_request_data, "host", None)
        if host is not None:
            record.host = host  # type: ignore[attr-defined]

        # Get X-Forwarded-For if configured
        if self.log_forwarded_for:
            x_forwarded_for = getattr(_request_data, "x_forwarded_for", None)
            if x_forwarded_for is not None:
                record.x_forwarded_for = x_forwarded_for  # type: ignore[attr-defined]

        # Get alternative client IP header if configured
        if self.client_ip_header:
            client_ip_value = getattr(_request_data, "client_ip_value", None)
            if client_ip_value is not None:
                record.client_ip_value = client_ip_value  # type: ignore[attr-defined]

        # Get response time if available
        response_time = getattr(_request_data, "response_time", None)
        if response_time is not None:
            record.response_time = response_time  # type: ignore[attr-defined]

        return True


class AccessLogMiddleware(BaseHTTPMiddleware):
    """Middleware to add request metadata (Host, X-Forwarded-For, response time) to access logs."""

    def __init__(
        self: "AccessLogMiddleware",
        app: object,
        log_forwarded_for: bool = False,
        client_ip_header: str | None = None,
    ) -> None:
        super().__init__(app)  # type: ignore[arg-type]
        self.log_forwarded_for = log_forwarded_for
        self.client_ip_header = client_ip_header

    async def dispatch(
        self: "AccessLogMiddleware", request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        """Process request and add request metadata to thread-local storage."""
        # Record start time
        start_time = time.perf_counter()

        # Store Host header in thread-local storage
        host = request.headers.get("Host")
        if host:
            _request_data.host = host

        # Store X-Forwarded-For if configured
        if self.log_forwarded_for:
            x_forwarded_for = request.headers.get("X-Forwarded-For")
            if x_forwarded_for:
                _request_data.x_forwarded_for = x_forwarded_for

        # Store alternative client IP header if configured
        if self.client_ip_header:
            client_ip_value = request.headers.get(self.client_ip_header)
            if client_ip_value:
                _request_data.client_ip_value = client_ip_value

        response = await call_next(request)

        # Calculate response time in milliseconds
        response_time_ms = (time.perf_counter() - start_time) * 1000
        _request_data.response_time = round(response_time_ms, 2)

        return response
