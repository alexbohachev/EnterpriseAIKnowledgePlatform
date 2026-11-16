#!/usr/bin/env python3
"""Write explicit NOT_EXECUTED records for rubric items outside MVP scope."""
from __future__ import annotations
from datetime import datetime, timezone
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REPORTS = ROOT / 'reports'
REPORTS.mkdir(parents=True, exist_ok=True)

OPEN_ITEMS = [
    {
        'id': 'semantic-knowledge-graph',
        'status': 'NOT_EXECUTED',
        'scope': 'Typed semantic relations beyond lexical GraphRAG-lite',
        'evidence_expected': 'Neo4j schema with relation types, precision/recall on labeled triples',
        'doc': 'docs/Stage8_Open_Requirements_UA.md#semantic-graph',
    },
    {
        'id': 'multimodal-drawings-tables',
        'status': 'NOT_EXECUTED',
        'scope': 'Engineering drawings and complex tables (OCR text-only today)',
        'evidence_expected': 'VLM or table pipeline metrics on annotated fixtures',
        'doc': 'docs/Stage8_Open_Requirements_UA.md#multimodal',
    },
    {
        'id': 'air-gap-audit',
        'status': 'NOT_EXECUTED',
        'scope': 'Host egress, DNS, image provenance, secret handling',
        'evidence_expected': 'Signed operator checklist + packet capture summary',
        'doc': 'docs/Stage8_Open_Requirements_UA.md#air-gap',
    },
    {
        'id': 'gpu-inference-benchmark',
        'status': 'NOT_EXECUTED',
        'scope': 'GPU tokens/s, TTFT, VRAM — not HTTP client RPS',
        'evidence_expected': 'Ollama server metrics with hardware SKU',
        'doc': 'docs/Stage8_Open_Requirements_UA.md#gpu-benchmark',
    },
]

def main():
    stamp = datetime.now(timezone.utc).isoformat()
    payload = {
        'generated_utc': stamp,
        'register': 'Stage8_OPEN_requirements',
        'items': OPEN_ITEMS,
        'acceptance': 'BLOCKED',
        'note': 'Presence of this file documents honesty; it is not a pass certificate.',
    }
    dest = REPORTS / 'open_requirements_register.json'
    dest.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding='utf-8')
    print(json.dumps(payload, indent=2, ensure_ascii=False))


if __name__ == '__main__':
    main()