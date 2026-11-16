#!/usr/bin/env python3
"""Fail-honest Stage8 evidence collection; never claims Docker ready without Docker."""
from __future__ import annotations
import argparse
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
from datetime import datetime, timezone

root = Path(__file__).resolve().parents[1]
RAG_EVAL_SCHEMA_VERSION = 2
LOAD_REPORT_SCHEMA_VERSION = 1

OPEN_SCOPE_BLOCKERS = [
    'Real GraphRAG model quality/semantic relations',
    'Multimodal diagrams/tables parsing',
    'Formal GPU/tokens-per-second benchmark (not client HTTP only)',
    'Air-gap and security operator evidence',
]


def _json_passed(path: Path) -> bool:
    if not path.is_file():
        return False
    try:
        return bool(json.loads(path.read_text(encoding='utf-8')).get('passed'))
    except (json.JSONDecodeError, OSError):
        return False


def _rag_eval_ok(path: Path, min_pass_rate: float = 1.0) -> bool:
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


def _load_query_ok(path: Path, max_p95_ms: float = 60_000) -> bool:
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


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument(
        '--require-mvp-live',
        action='store_true',
        default=bool(os.getenv('EAKP_REQUIRE_MVP_LIVE')),
        help='Exit non-zero unless synthetic Docker MVP gates pass',
    )
    args = p.parse_args()

    pr = subprocess.run(
        [sys.executable, '-m', 'pytest', '-o', 'addopts=', '--disable-warnings'],
        cwd=root,
        capture_output=True,
        text=True,
        timeout=180,
    )
    try:
        import yaml
        compose = yaml.safe_load((root / 'compose.yaml').read_text(encoding='utf-8'))
        valid_compose = isinstance(compose, dict) and isinstance(compose.get('services'), dict)
    except ImportError:
        valid_compose = False

    reports = root / 'reports'
    live_smoke = _json_passed(reports / 'integration_smoke.json')
    live_ocr = _json_passed(reports / 'ocr_live_e2e.json')
    live_rag = _rag_eval_ok(reports / 'rag_eval.json')
    live_rag_bob = _rag_eval_ok(reports / 'rag_eval_bob_acl.json')
    live_load_ok = _load_query_ok(reports / 'load_query.json')

    mvp_blockers: list[str] = []
    if not live_smoke:
        mvp_blockers.append('Docker-based E2E and ACL + scanned PDF proof')
    if not live_ocr:
        mvp_blockers.append('Live OCR scanned-PDF operator proof')
    if not live_rag:
        mvp_blockers.append('RAG evaluation failed quality gate (rag_eval.json)')
    if not live_rag_bob:
        mvp_blockers.append('Bob ACL RAG evaluation failed quality gate (rag_eval_bob_acl.json)')
    if not live_load_ok:
        mvp_blockers.append('Query load benchmark failed quality gate (load_query.json)')

    mvp_acceptance = 'PASS' if not mvp_blockers else 'BLOCKED'
    release_blockers = mvp_blockers + OPEN_SCOPE_BLOCKERS
    live_status = 'EXECUTED' if live_smoke else 'NOT_EXECUTED'

    record = {
        'project': 'EAKP Stage 8',
        'generated_utc': datetime.now(timezone.utc).isoformat(),
        'ocr_engine_available': bool(shutil.which('tesseract')),
        'docker_engine_command_available': bool(shutil.which('docker')),
        'compose_yaml_parse': valid_compose,
        'pytest_status': 'PASS' if pr.returncode == 0 else 'FAIL',
        'pytest_summary': (pr.stdout + pr.stderr)[-1500:],
        'test_scope': 'SQLite+HTTP tests with simulated AI/index adapters; actual local Tesseract OCR on synthetic scans',
        'live_qdrant_neo4j_ollama_e2e': live_status,
        'live_ocr_e2e': 'EXECUTED' if live_ocr else 'NOT_EXECUTED',
        'live_rag_eval': 'PASS' if live_rag else 'NOT_EXECUTED',
        'live_rag_bob_acl': 'PASS' if live_rag_bob else 'NOT_EXECUTED',
        'live_load_query_report': (
            'PASS' if live_load_ok else ('PRESENT' if (reports / 'load_query.json').is_file() else 'MISSING')
        ),
        'mvp_acceptance': mvp_acceptance,
        'mvp_blockers': mvp_blockers,
        'scope_blockers': OPEN_SCOPE_BLOCKERS,
        'air_gap_certification': 'NOT_EXECUTED',
        'gpu_inference_benchmark': 'NOT_EXECUTED',
        'security_pentest': 'NOT_EXECUTED',
        'rag_eval_schema_version_required': RAG_EVAL_SCHEMA_VERSION,
        'load_report_schema_version_required': LOAD_REPORT_SCHEMA_VERSION,
        'release_acceptance': 'BLOCKED' if release_blockers else 'ACCEPTED',
        'blockers': release_blockers,
        'evidence_files': {
            'integration_smoke': str(reports / 'integration_smoke.json') if live_smoke else None,
            'ocr_live_e2e': str(reports / 'ocr_live_e2e.json') if live_ocr else None,
            'load_query': str(reports / 'load_query.json') if live_load_ok else None,
            'rag_eval': str(reports / 'rag_eval.json') if live_rag else None,
            'rag_eval_bob_acl': str(reports / 'rag_eval_bob_acl.json') if live_rag_bob else None,
        },
    }
    out = root / 'reports/stage8_preflight.json'
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(record, indent=2, ensure_ascii=False), encoding='utf-8')
    print(json.dumps(record, indent=2, ensure_ascii=False))

    if pr.returncode != 0 or not valid_compose:
        return 2
    if args.require_mvp_live and mvp_acceptance != 'PASS':
        return 2
    return 0


if __name__ == '__main__':
    sys.exit(main())