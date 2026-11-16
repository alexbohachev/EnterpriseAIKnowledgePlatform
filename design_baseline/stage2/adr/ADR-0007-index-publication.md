# ADR-0007 — Two-stage index publication

**Status:** Proposed | **Date:** 2026-11-16

## Context
Qdrant and Neo4j do not share an atomic transaction. Partial writes must not become search-visible.

## Decision
Create immutable document_version + index_run_id. Stage writes in Qdrant and Neo4j under run id; verify both; **one PostgreSQL transaction** updates documents.active_index_run_id. Readers filter on active run; failed/stale runs ignored and eventually garbage-collected.

## Alternatives
Dual-write visible immediately is rejected (partial context). Eventual consistency alone insufficient for reproducible queries.

## Trade-offs
Requires extra storage/verification and cleanup, but provides readable atomic publication.

## Verification
AT-10 worker crash between writes, retries, invariant INV-04.
