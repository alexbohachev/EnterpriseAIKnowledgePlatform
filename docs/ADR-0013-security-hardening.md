# ADR-0013 — MVP defense in depth (Stage 5)

Status: Accepted for local MVP. Not security certification.

**Decision.** Enforce SQL ACL as only authority; add fail-closed invalid-token revocation by monotonic `users.token_version` and JWT `ver`; use per-process request limits (remote socket IP on login; user ID on query/upload); use deterministic PII masking and untrusted-content instruction filtering before local LLM; reject missing/out-of-range model citation IDs; restrict local service URLs by allowlist; bypass HTTP_PROXY via `trust_env=False`; apply no-store/security headers and container confinement.

**Limitations.** In-process limiting doesn't aggregate multiple replicas or survive restarts; regex masks miss obfuscated/nonstandard PII and prompt injections; sanitizing excerpts may hide relevant evidence; validation doesn't establish response truth; access changes during a network response can't be withdrawn. Runtime secrets remain provided via env variables (Docker inspect risk). Graph entity labels can reveal data to Neo4j operators. No TLS edge/gateway, malware scanning, hardened PDF sandbox, key rotation process, external audit, penetration testing or real Docker integration test. Requires security review and layered controls before deployment.

**Rejected.** Directly trusting Qdrant payload ACL and reliance on system prompt alone. Both fail closed-policy objectives.
