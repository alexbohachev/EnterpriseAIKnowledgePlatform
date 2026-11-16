#!/usr/bin/env python3
"""Shared JSON quality gates for synthetic Docker MVP evidence (reports/)."""
from __future__ import annotations
import json
from pathlib import Path

RAG_EVAL_SCHEMA_VERSION = 2
LOAD_REPORT_SCHEMA_VERSION = 1
EVIDENCE_BUNDLE_SCHEMA_VERSION = 1

REQUIRED_MVP_ARTIFACTS = (
    'integration_smoke.json',
    'ocr_live_e2e.json',
    'rag_eval.json',
    'rag_eval_bob_acl.json',
    'load_query.json',
    'stage8_preflight.json',
)


def _json_passed(path: Path) -> bool:
    if not path.is_file():
        return False
    try:
        return bool(json.loads(path.read_text(encoding='utf-8')).get('passed'))
    except (json.JSONDecodeError, OSError):
        return False


def rag_eval_ok(path: Path, min_pass_rate: float = 1.0) -> bool:
    if not path.is_file():
        return False
    try:
        body = json.loads(path.read_text(encoding='utf-8'))
        if body.get('eval_schema_version', 0) < RAG_EVAL_SCHEMA_VERSION:
            return False
        required = {'quality_failures', 'quality_pass_rate', 'faithfulness_pass_rate', 'completed', 'failed'}
        if not required.issubset(body.keys()):
            return False
        if not isinstance(body['quality_failures'], int):
            return False
        rate = body['quality_pass_rate']
        faith = body['faithfulness_pass_rate']
        if rate is None or faith is None:
            return False
        return (
            body['failed'] == 0
            and body['completed'] > 0
            and rate >= min_pass_rate
            and faith >= min_pass_rate
        )
    except (json.JSONDecodeError, OSError, TypeError):
        return False


def load_query_ok(path: Path, max_p95_ms: float = 60_000) -> bool:
    if not path.is_file():
        return False
    try:
        body = json.loads(path.read_text(encoding='utf-8'))
        p95 = (body.get('latency_ms') or {}).get('p95')
        ratio = body.get('http_success_ratio')
        if body.get('report_schema_version', 0) < LOAD_REPORT_SCHEMA_VERSION:
            return False
        return (
            body.get('mode') == 'query'
            and ratio is not None
            and ratio >= 0.99
            and p95 is not None
            and p95 <= max_p95_ms
            and body.get('provenance') == 'live_http_client_side'
        )
    except (json.JSONDecodeError, OSError):
        return False


def assess_mvp(reports_dir: Path) -> tuple[str, list[str]]:
    reports_dir = Path(reports_dir)
    blockers: list[str] = []
    if not _json_passed(reports_dir / 'integration_smoke.json'):
        blockers.append('integration_smoke.json missing or passed!=true')
    if not _json_passed(reports_dir / 'ocr_live_e2e.json'):
        blockers.append('ocr_live_e2e.json missing or passed!=true')
    if not rag_eval_ok(reports_dir / 'rag_eval.json'):
        blockers.append('rag_eval.json failed schema v2 / quality gates')
    if not rag_eval_ok(reports_dir / 'rag_eval_bob_acl.json'):
        blockers.append('rag_eval_bob_acl.json failed schema v2 / quality gates')
    if not load_query_ok(reports_dir / 'load_query.json'):
        blockers.append('load_query.json failed schema v1 / load gates')
    preflight = reports_dir / 'stage8_preflight.json'
    if not preflight.is_file():
        blockers.append('stage8_preflight.json missing (run preflight --require-mvp-live)')
    else:
        try:
            body = json.loads(preflight.read_text(encoding='utf-8'))
            if body.get('mvp_acceptance') != 'PASS':
                blockers.append('stage8_preflight.json mvp_acceptance != PASS')
        except (json.JSONDecodeError, OSError):
            blockers.append('stage8_preflight.json unreadable')
    return ('PASS' if not blockers else 'BLOCKED'), blockers