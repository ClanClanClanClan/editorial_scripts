"""
OpenTelemetry Observability Stack Implementation

Implements Section 7 of ECC specifications:
- Service Level Objectives (SLOs)
- Distributed tracing
- Prometheus metrics
- Error tracking and alerting
- Performance monitoring
"""

import asyncio
import time
from collections.abc import Callable
from contextlib import asynccontextmanager
from dataclasses import dataclass
from functools import wraps
from typing import Any

# Optional OpenTelemetry imports - system works without them
try:
    from opentelemetry import metrics, trace
    from opentelemetry.exporter.jaeger.thrift import JaegerExporter
    from opentelemetry.exporter.prometheus import PrometheusMetricReader
    from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
    from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor
    from opentelemetry.sdk.metrics import MeterProvider
    from opentelemetry.sdk.resources import SERVICE_NAME, SERVICE_VERSION, Resource
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import BatchSpanProcessor
    from opentelemetry.semconv.trace import SpanAttributes

    OTEL_AVAILABLE = True
except ImportError:
    # Mock objects when OpenTelemetry is not available
    trace = None
    metrics = None
    OTEL_AVAILABLE = False

from src.ecc.core.logging_system import ExtractorLogger


@dataclass
class ObservabilityConfig:
    """Configuration for ECC observability stack per Section 7.2."""

    service_name: str = "editorial-command-center"
    service_version: str = "2.0.0"
    environment: str = "production"

    # Tracing
    enable_tracing: bool = True
    jaeger_endpoint: str | None = "http://localhost:14268/api/traces"
    trace_sample_rate: float = 1.0

    # Metrics
    enable_metrics: bool = True
    prometheus_port: int = 8090
    metrics_export_interval: int = 30

    # SLOs (from Section 7.1)
    api_availability_target: float = 0.999  # 99.9%
    manuscript_sync_latency_p95: float = 30.0  # 30s
    manuscript_sync_latency_p99: float = 60.0  # 60s
    ai_analysis_accuracy_target: float = 0.85  # 85%
    data_freshness_target: float = 900.0  # 15 minutes

    # Auto-instrumentation
    enable_auto_instrumentation: bool = True


class ECCObservability:
    """
    OpenTelemetry observability implementation for ECC.

    Implements the complete observability stack from Section 7 of specifications:
    - Distributed tracing with Jaeger
    - Prometheus metrics with SLOs
    - Custom instrumentation for editorial operations
    - Error tracking and alerting
    """

    def __init__(self, config: ObservabilityConfig, logger: ExtractorLogger | None = None):
        """Initialize observability stack."""
        self.config = config
        self.logger = logger or ExtractorLogger("observability")

        # OpenTelemetry components
        self.tracer_provider: TracerProvider | None = None
        self.meter_provider: MeterProvider | None = None
        self.tracer = None
        self.meter = None

        # Custom metrics for ECC operations
        self.http_requests_total = None
        self.http_request_duration = None
        self.manuscript_sync_duration = None
        self.ai_analysis_total = None
        self.ai_human_agreement_total = None
        self.journal_errors_total = None

        # SLO tracking
        self.slo_targets = self._initialize_slo_targets()

    def _initialize_slo_targets(self) -> dict[str, float]:
        """Initialize SLO targets from configuration."""
        return {
            "api_availability": self.config.api_availability_target,
            "manuscript_sync_p95": self.config.manuscript_sync_latency_p95,
            "manuscript_sync_p99": self.config.manuscript_sync_latency_p99,
            "ai_accuracy": self.config.ai_analysis_accuracy_target,
            "data_freshness": self.config.data_freshness_target,
        }

    async def initialize(self):
        """Initialize the complete observability stack."""
        try:
            if not OTEL_AVAILABLE:
                self.logger.log_warning("OpenTelemetry not available - observability disabled")
                return

            self.logger.log_info("Initializing ECC observability stack")

            # Create resource
            resource = Resource.create(
                {
                    SERVICE_NAME: self.config.service_name,
                    SERVICE_VERSION: self.config.service_version,
                    "environment": self.config.environment,
                    "component": "ecc-core",
                }
            )

            # Initialize tracing
            if self.config.enable_tracing:
                await self._setup_tracing(resource)

            # Initialize metrics
            if self.config.enable_metrics:
                await self._setup_metrics(resource)

            # Setup auto-instrumentation
            if self.config.enable_auto_instrumentation:
                self._setup_auto_instrumentation()

            self.logger.log_success("Observability stack initialized successfully")

        except Exception as e:
            self.logger.log_error(f"Failed to initialize observability: {e}")
            # Continue without telemetry rather than failing completely

    async def _setup_tracing(self, resource):
        """Setup distributed tracing with Jaeger."""
        if not OTEL_AVAILABLE:
            return

        # Create tracer provider
        self.tracer_provider = TracerProvider(resource=resource)
        trace.set_tracer_provider(self.tracer_provider)

        # Setup Jaeger exporter if configured
        if self.config.jaeger_endpoint:
            jaeger_exporter = JaegerExporter(endpoint=self.config.jaeger_endpoint)
            span_processor = BatchSpanProcessor(jaeger_exporter)
            self.tracer_provider.add_span_processor(span_processor)

        # Get tracer for ECC operations
        self.tracer = trace.get_tracer(
            instrumenting_module_name="ecc.core",
            instrumenting_library_version=self.config.service_version,
        )

        self.logger.log_info("Distributed tracing configured with Jaeger")

    async def _setup_metrics(self, resource):
        """Setup Prometheus metrics collection."""
        if not OTEL_AVAILABLE:
            return

        # Create metric readers
        readers = []

        # Prometheus reader for SLO monitoring
        if self.config.prometheus_port:
            prometheus_reader = PrometheusMetricReader(
                endpoint=f"0.0.0.0:{self.config.prometheus_port}"
            )
            readers.append(prometheus_reader)

        # Create meter provider
        self.meter_provider = MeterProvider(resource=resource, metric_readers=readers)
        metrics.set_meter_provider(self.meter_provider)

        # Get meter for ECC metrics
        self.meter = metrics.get_meter(name="ecc.core", version=self.config.service_version)

        # Create ECC-specific metrics (Section 7.1 SLOs)
        self._create_ecc_metrics()

        self.logger.log_info("Prometheus metrics configured")

    def _create_ecc_metrics(self):
        """Create custom metrics for ECC operations."""
        if not self.meter:
            return

        # HTTP request metrics for API availability SLO
        self.http_requests_total = self.meter.create_counter(
            name="http_requests_total",
            description="Total HTTP requests by method, endpoint, status",
            unit="1",
        )

        self.http_request_duration = self.meter.create_histogram(
            name="http_request_duration_seconds",
            description="HTTP request duration in seconds",
            unit="s",
        )

        # Manuscript sync metrics for latency SLO
        self.manuscript_sync_duration = self.meter.create_histogram(
            name="manuscript_sync_duration_seconds",
            description="Manuscript synchronization duration",
            unit="s",
        )

        # AI analysis metrics for accuracy SLO
        self.ai_analysis_total = self.meter.create_counter(
            name="ai_analysis_total",
            description="Total AI analysis operations by journal, type",
            unit="1",
        )

        self.ai_human_agreement_total = self.meter.create_counter(
            name="ai_human_agreement_total",
            description="AI predictions that agree with human review",
            unit="1",
        )

        # Journal operation error tracking
        self.journal_errors_total = self.meter.create_counter(
            name="journal_errors_total",
            description="Journal adapter errors by journal, error_type",
            unit="1",
        )

        # Data freshness metric
        self.time_since_last_sync = self.meter.create_gauge(
            name="time_since_last_sync_seconds",
            description="Time since last successful sync by journal",
            unit="s",
        )

    def _setup_auto_instrumentation(self):
        """Setup automatic instrumentation for common libraries."""
        if not OTEL_AVAILABLE:
            return

        try:
            # Instrument FastAPI automatically
            FastAPIInstrumentor().instrument()

            # Instrument SQLAlchemy for database operations
            SQLAlchemyInstrumentor().instrument()

            self.logger.log_info("Auto-instrumentation configured")

        except Exception as e:
            self.logger.log_warning(f"Auto-instrumentation setup failed: {e}")

    @asynccontextmanager
    async def trace_journal_operation(
        self, operation_name: str, journal_id: str, manuscript_id: str | None = None
    ):
        """
        Context manager for tracing journal operations.

        Implements custom instrumentation for ECC journal adapters.
        """
        if not self.tracer:
            yield
            return

        with self.tracer.start_as_current_span(
            name=f"journal.{operation_name}",
            attributes={
                SpanAttributes.SERVICE_NAME: self.config.service_name,
                "journal.id": journal_id,
                "operation.name": operation_name,
                "manuscript.id": manuscript_id or "unknown",
            },
        ) as span:
            start_time = time.time()

            try:
                yield span

                # Record success metrics
                if operation_name == "sync_manuscripts":
                    duration = time.time() - start_time
                    if self.manuscript_sync_duration:
                        self.manuscript_sync_duration.record(
                            duration, attributes={"journal": journal_id, "status": "success"}
                        )

            except Exception as e:
                # Record error in span and metrics
                span.set_status(trace.Status(trace.StatusCode.ERROR, str(e)))
                span.record_exception(e)

                if self.journal_errors_total:
                    self.journal_errors_total.add(
                        1,
                        attributes={
                            "journal": journal_id,
                            "operation": operation_name,
                            "error_type": type(e).__name__,
                        },
                    )

                raise

    def record_ai_analysis(
        self, journal_id: str, analysis_type: str, human_agreement: bool, confidence_score: float
    ):
        """Record AI analysis metrics for accuracy SLO."""
        if not self.ai_analysis_total:
            return

        # Record total analysis
        self.ai_analysis_total.add(
            1,
            attributes={
                "journal": journal_id,
                "analysis_type": analysis_type,
                "confidence_bucket": self._get_confidence_bucket(confidence_score),
            },
        )

        # Record human agreement for accuracy calculation
        if human_agreement and self.ai_human_agreement_total:
            self.ai_human_agreement_total.add(
                1, attributes={"journal": journal_id, "analysis_type": analysis_type}
            )

    def _get_confidence_bucket(self, score: float) -> str:
        """Bucket confidence scores for metrics."""
        if score >= 0.9:
            return "high"
        elif score >= 0.7:
            return "medium"
        else:
            return "low"

    def record_http_request(self, method: str, endpoint: str, status_code: int, duration: float):
        """Record HTTP request metrics for API availability SLO."""
        if not self.http_requests_total:
            return

        labels = {"method": method, "endpoint": endpoint, "status": str(status_code)}

        self.http_requests_total.add(1, labels)

        if self.http_request_duration:
            self.http_request_duration.record(duration, labels)

    def update_data_freshness(self, journal_id: str, last_sync_timestamp: float):
        """Update data freshness metrics."""
        if self.time_since_last_sync:
            current_time = time.time()
            time_since_sync = current_time - last_sync_timestamp

            self.time_since_last_sync.set(time_since_sync, attributes={"journal": journal_id})

    def get_trace_context(self) -> dict[str, Any]:
        """Get current trace context for correlation."""
        if not self.tracer:
            return {}

        span = trace.get_current_span()
        if span and span.get_span_context():
            span_context = span.get_span_context()
            return {
                "trace_id": format(span_context.trace_id, "032x"),
                "span_id": format(span_context.span_id, "016x"),
                "trace_flags": span_context.trace_flags,
            }

        return {}

    async def shutdown(self):
        """Shutdown observability providers gracefully."""
        try:
            if self.tracer_provider:
                self.tracer_provider.shutdown()

            if self.meter_provider:
                self.meter_provider.shutdown()

            self.logger.log_info("Observability stack shut down successfully")

        except Exception as e:
            self.logger.log_error(f"Error during observability shutdown: {e}")


# Global observability instance
_observability_instance: ECCObservability | None = None


def initialize_observability(
    config: ObservabilityConfig | None = None, logger: ExtractorLogger | None = None
) -> ECCObservability:
    """Initialize global observability instance."""
    global _observability_instance

    if config is None:
        config = ObservabilityConfig()

    _observability_instance = ECCObservability(config, logger)
    return _observability_instance


def get_observability() -> ECCObservability | None:
    """Get global observability instance."""
    return _observability_instance


def trace_operation(operation_name: str, journal_id: str = "system"):
    """Convenience function for tracing operations."""
    obs = get_observability()
    if obs:
        return obs.trace_journal_operation(operation_name, journal_id)
    else:
        # Return no-op context manager
        return asynccontextmanager(lambda: (yield))()


def trace_method(operation_name: str | None = None):
    """Convenience decorator for tracing methods."""

    def decorator(func: Callable) -> Callable:
        obs = get_observability()
        if not obs or not obs.tracer:
            return func

        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            span_name = operation_name or f"{func.__module__}.{func.__name__}"

            with obs.tracer.start_as_current_span(span_name) as span:
                try:
                    result = await func(*args, **kwargs)
                    return result
                except Exception as e:
                    span.set_status(trace.Status(trace.StatusCode.ERROR, str(e)))
                    span.record_exception(e)
                    raise

        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            span_name = operation_name or f"{func.__module__}.{func.__name__}"

            with obs.tracer.start_as_current_span(span_name) as span:
                try:
                    result = func(*args, **kwargs)
                    return result
                except Exception as e:
                    span.set_status(trace.Status(trace.StatusCode.ERROR, str(e)))
                    span.record_exception(e)
                    raise

        # Return appropriate wrapper
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper

    return decorator
