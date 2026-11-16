# ADR-0006 — PostgreSQL як джерело ACL, epoch-based final gate

**Status:** Proposed | **Date:** 2026-11-16

## Context
Derived vector/graph indexes can contain stale access metadata. Source OTUS requires no cross-user leakage.

## Decision
Authoritative access grants and document.acl_epoch live in PostgreSQL. Both retrieval and graph expansion use scoped prefilter; **after** retrieval gate checks all candidate provenance; before output gate re-checks doc ACL epoch. In MVP, do not stream secret text before final check.

## Alternatives
Index-only ACL rejected (eventual consistency); one-time access check rejected (revoke race).

## Trade-offs
Extra DB queries and latency; reliable fail-closed control.

## Verification
AT-02, AT-03, AT-04; invalidation and revoke-race.
