"""Low-cardinality metrics and optional local-only OpenTelemetry tracing.

Never record prompts, model outputs, JWTs, document titles, user identifiers or
arbitrary request paths as label values/span attributes. Monitoring is not a
security boundary, and sensitive content stays out of telemetry by design.
"""
from __future__ import annotations
from contextlib import contextmanager
import re
import time
from typing import Generator

from prometheus_client import CollectorRegistry, Counter, Gauge, Histogram, generate_latest, CONTENT_TYPE_LATEST
from opentelemetry import trace
from opentelemetry.trace import SpanKind

ROUTE_FALLBACK = "unmatched"
STAGES = frozenset({"retrieval", "generation"})
HTTP_BUCKETS = (0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1, 2.5, 5, 10, 30, 60)
RAG_BUCKETS = (0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1, 2.5, 5, 10, 30, 60, 120)


def safe_route(path: str | None) -> str:
    """Only known, static path templates, never user-controlled raw IDs."""
    if not path or len(path) > 150 or not path.startswith("/"):
        return ROUTE_FALLBACK
    if re.search(r"[^a-zA-Z0-9/_{}-]", path):
        return ROUTE_FALLBACK
    # Literal UUID paths must never show up in labels.
    if re.search(r"[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-", path):
        return ROUTE_FALLBACK
    return path


class Observability:
    def __init__(self) -> None:
        self.registry = CollectorRegistry(auto_describe=True)
        self.requests = Counter("eakp_http_requests_total", "Completed HTTP requests", ["method", "route", "status_class"], registry=self.registry)
        self.duration = Histogram("eakp_http_request_duration_seconds", "HTTP server elapsed time", ["method", "route"], buckets=HTTP_BUCKETS, registry=self.registry)
        self.inflight = Gauge("eakp_http_requests_inflight", "In-flight HTTP requests", registry=self.registry)
        self.rag_duration = Histogram("eakp_rag_stage_duration_seconds", "Local RAG stage latency", ["stage", "outcome"], buckets=RAG_BUCKETS, registry=self.registry)
        self.rag_excerpts = Histogram("eakp_rag_retrieved_excerpts", "Authorized excerpts returned by retrieval", buckets=(0, 1, 2, 3, 4, 5, 6, 10, 20), registry=self.registry)

    def render(self) -> bytes:
        return generate_latest(self.registry)

    @contextmanager
    def stage(self, name: str) -> Generator[None, None, None]:
        if name not in STAGES:
            raise ValueError("Unexpected telemetry stage")
        started = time.perf_counter()
        outcome = "ok"
        with trace.get_tracer("eakp.rag").start_as_current_span(f"rag.{name}", kind=SpanKind.INTERNAL):
            try:
                yield
            except Exception:
                outcome = "error"
                raise
            finally:
                self.rag_duration.labels(stage=name, outcome=outcome).observe(time.perf_counter() - started)


def configure_tracing(local_endpoint: str, service_name: str = "eakp-api") -> None:
    """Enable OTLP/HTTP only when explicitly configured on a local destination."""
    if not local_endpoint:
        return
    from opentelemetry.sdk.resources import Resource
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import BatchSpanProcessor
    from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
    from opentelemetry.sdk.trace.sampling import ParentBased, TraceIdRatioBased

    if isinstance(trace.get_tracer_provider(), TracerProvider):
        return  # Tests may create many apps; process global provider must not be overwritten.
    provider = TracerProvider(resource=Resource.create({"service.name": service_name}),
                              sampler=ParentBased(TraceIdRatioBased(0.1)))
    provider.add_span_processor(BatchSpanProcessor(OTLPSpanExporter(endpoint=local_endpoint,
                                                                     timeout=3)))
    trace.set_tracer_provider(provider)
