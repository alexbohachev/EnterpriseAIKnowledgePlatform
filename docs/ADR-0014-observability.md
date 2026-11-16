# ADR-0014: Opt-in local Observability for GraphRAG

**Status:** Accepted for Stage 6 MVP (requires runtime verification before deployment).

## Context
Enterprise AI requests may span PostgreSQL ACL, Qdrant, Neo4j, local embeddings and local LLM generation. API health alone does not capture inference latency, error rates and safe retrieval behavior. Full payload capture is unacceptable for corporate data.

## Decision
Implement `prometheus_client` with a per-app registry and bounded path-template + status-class labels. Use `opentelemetry-sdk` with exporter enabled explicitly for **local OTLP/HTTP endpoint only**, a 10% parent-based trace sampler, and fixed stage spans (retrieval, generation). Provide an optional Docker Compose monitoring profile for Prometheus, Grafana, Jaeger, OTel Collector. Restrict operational UI to loopback and use a dedicated bearer token for API metrics.

## Rejected alternatives
- Prompts/answers as trace attributes: high PII and secret exfiltration risk.
- Arbitrary HTTP raw paths as metrics labels: unbounded cardinality and leaked identifiers.
- Public hosted observability: violates Stage 1 offline goal.
- Grafana scrape directly from worker/indexer with unauthenticated public ports: risk out of proportion for MVP.

## Consequences / risk acceptance
- API telemetry covers only API operations and RAG endpoint stages; background pipelines lack scraped metrics (container logs and SQL job states are used operationally).
- Per-process metrics lose counters on restart; Prometheus keeps historical samples when running.
- 10% sampled spans are insufficient for exhaustive audit; sensitive audit remains in separate SQL audit table.
- Traces are useful for debugging but **cannot be trusted as business/audit truth**.
- Metrics endpoint bearer token, local port bindings and network ACL are defense-in-depth, not replacements for hardened reverse proxy/TLS/firewall.
- True Docker service integration and tracing exporter have not been executed in the current development environment.
