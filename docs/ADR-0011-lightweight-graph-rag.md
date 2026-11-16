# ADR-0011 — Lexical entity graph before semantic KG extraction

Status: Provisional. This is an MVP architecture choice, not a claim of full GraphRAG completeness.

Decision: Qdrant for semantic seed retrieval, Neo4j graph `Document-HAS_CHUNK-Chunk-MENTIONS-Entity` using deterministic acronym/proper-name rules. Expand vector seeds along shared entities, then reapply SQL ACL.

Benefits: demonstrable self-hosted vector + graph augmentation without training or a second LLM call during ingestion; straightforward provenance.

Limitations: misses lower-case entities, false positives, no typed relations or entity normalization. Does not meet every interpretation of 'knowledge graph'; Stage 4 needs evaluation, and future versions should perform constrained local entity/relation extraction with human review.
