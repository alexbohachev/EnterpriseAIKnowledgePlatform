# ADR-0010 — SQL ACL-gated retrieval and publication pointer

Status: Accepted for prototype; production validation pending.

Decision: DB owns ACL and active_index_run_id. Qdrant/Neo4j never authorize or return raw text. Query prefilters document IDs and active run IDs, then validates each chunk via authoritative SQL both before LLM invocation and after completion. When access changes, cancel response with 409.

Rationale: external indexes may be stale after ACL changes, contain orphans after failed distributed writes, or include graph edges to confidential material. They cannot be trusted for authorization.

Cost: duplicate SQL lookup per chunk; bounded MVP scan; additional p95. Production plan: indexed ACL joins, cache invalidation keyed by ACL epoch, deletion/reconciliation, mutation race tests.
