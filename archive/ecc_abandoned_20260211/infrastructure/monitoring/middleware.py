"""
FastAPI Observability Middleware

Implements Section 7.2 observability middleware from ECC specifications:
- Request/response tracking
- Distributed tracing
- SLO metrics collection
- Error correlation
"""

import time
import uuid
from collections.abc import Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from src.ecc.infrastructure.monitoring import get_observability

# Optional OpenTelemetry imports for status handling
try:
    from opentelemetry import trace

    TRACE_AVAILABLE = True
except ImportError:
    trace = None
    TRACE_AVAILABLE = False


class ObservabilityMiddleware(BaseHTTPMiddleware):
    """
    FastAPI middleware for comprehensive observability.

    Implements the observability middleware pattern from Section 7.2:
    - Automatic request tracing
    - SLO metrics collection
    - Error correlation
    - Performance monitoring
    """

    def __init__(self, app):
        super().__init__(app)
        self.observability = get_observability()

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process request with full observability."""

        # Generate request ID for correlation
        request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
        request.state.request_id = request_id

        # Skip health check endpoints from detailed tracing
        if request.url.path in ["/health", "/ready", "/metrics"]:
            return await call_next(request)

        # Start timing
        start_time = time.time()

        # Create trace context if observability is available
        if self.observability and self.observability.tracer:
            with self.observability.tracer.start_as_current_span(
                f"{request.method} {request.url.path}",
                attributes={
                    "http.method": request.method,
                    "http.url": str(request.url),
                    "http.scheme": request.url.scheme,
                    "http.host": request.url.hostname,
                    "http.target": request.url.path,
                    "request.id": request_id,
                    "user_agent": request.headers.get("user-agent", ""),
                },
            ) as span:
                try:
                    response = await call_next(request)

                    # Calculate duration
                    duration = time.time() - start_time

                    # Set span attributes for response
                    span.set_attribute("http.status_code", response.status_code)
                    span.set_attribute(
                        "http.response_size", response.headers.get("content-length", 0)
                    )

                    # Record metrics for SLO tracking
                    if self.observability:
                        self.observability.record_http_request(
                            method=request.method,
                            endpoint=request.url.path,
                            status_code=response.status_code,
                            duration=duration,
                        )

                    # Add correlation headers
                    response.headers["X-Request-ID"] = request_id
                    response.headers["X-Trace-ID"] = format(
                        span.get_span_context().trace_id, "032x"
                    )

                    return response

                except Exception as e:
                    # Record error in span
                    span.record_exception(e)
                    if TRACE_AVAILABLE and trace:
                        span.set_status(trace.Status(trace.StatusCode.ERROR, str(e)))

                    # Record error metrics
                    duration = time.time() - start_time
                    if self.observability:
                        self.observability.record_http_request(
                            method=request.method,
                            endpoint=request.url.path,
                            status_code=500,
                            duration=duration,
                        )

                    raise
        else:
            # No observability available, just process request
            response = await call_next(request)
            response.headers["X-Request-ID"] = request_id
            return response
