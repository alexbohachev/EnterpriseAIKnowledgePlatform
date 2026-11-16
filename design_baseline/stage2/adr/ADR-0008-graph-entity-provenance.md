# ADR-0008 — Document-scoped graph entities with provenance

**Status:** Proposed | **Date:** 2026-11-16

## Context
Global entity nodes/summaries may leak confidential relations even if source chunks are hidden.

## Decision
Each Document/Chunk/Entity is document-version scoped. Each relationship stores provenance to chunks and index_run_id. Any cross-document reasoning merges identities **only inside an authorized query view** and runs authoritative ACL checks before evidence reaches the LLM.

## Alternatives
Global de-duplicated knowledge graph rejected for MVP due to ACL complexity.

## Trade-offs
More graph nodes and weaker cross-document dedupe, but testable tenant/document isolation.

## Verification
AT-03 graph traversal and derived-metadata leakage tests.
