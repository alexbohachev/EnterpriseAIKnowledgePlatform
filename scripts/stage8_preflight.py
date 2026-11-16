#!/usr/bin/env python3
"""Fail-honest Stage8 evidence collection; never claims Docker ready without Docker."""
import json
from pathlib import Path
import shutil
import subprocess
import sys
from datetime import datetime, timezone

root=Path(__file__).resolve().parents[1]
pr=subprocess.run([sys.executable,'-m','pytest','-o','addopts=','--disable-warnings'],cwd=root,
                  capture_output=True,text=True,timeout=180)
try:
    import yaml
    compose=yaml.safe_load((root/'compose.yaml').read_text())
    valid_compose=isinstance(compose,dict) and isinstance(compose.get('services'),dict)
except ImportError:
    valid_compose=False
def _json_passed(path: Path) -> bool:
    if not path.is_file():
        return False
    try:
        return bool(json.loads(path.read_text(encoding='utf-8')).get('passed'))
    except (json.JSONDecodeError, OSError):
        return False

reports = root / 'reports'
live_smoke = _json_passed(reports / 'integration_smoke.json')
live_ocr = _json_passed(reports / 'ocr_live_e2e.json')
def _rag_eval_ok(path: Path, min_pass_rate: float = 1.0) -> bool:
    if not path.is_file():
        return False
    try:
        body = json.loads(path.read_text(encoding='utf-8'))
        rate = body.get('quality_pass_rate')
        if rate is None and body.get('completed', 0) > 0:
            rate = 1.0 - (body.get('quality_failures', 0) / body['completed'])
        return (
            body.get('failed', 1) == 0
            and body.get('completed', 0) > 0
            and rate is not None
            and rate >= min_pass_rate
        )
    except (json.JSONDecodeError, OSError):
        return False

def _load_query_ok(path: Path, max_p95_ms: float = 60_000) -> bool:
    if not path.is_file():
        return False
    try:
        body = json.loads(path.read_text(encoding='utf-8'))
        p95 = (body.get('latency_ms') or {}).get('p95')
        ratio = body.get('http_success_ratio')
        return (
            body.get('mode') == 'query'
            and ratio is not None
            and ratio >= 0.99
            and p95 is not None
            and p95 <= max_p95_ms
        )
    except (json.JSONDecodeError, OSError):
        return False

live_rag = _rag_eval_ok(reports / 'rag_eval.json')
live_rag_bob = _rag_eval_ok(reports / 'rag_eval_bob_acl.json')
live_load_ok = _load_query_ok(reports / 'load_query.json')

blockers = []
if not live_smoke:
    blockers.append('Docker-based E2E and ACL + scanned PDF proof')
if not live_ocr:
    blockers.append('Live OCR scanned-PDF operator proof')
blockers.extend([
    'Real GraphRAG model quality/semantic relations',
    'Multimodal diagrams/tables parsing',
    'Formal GPU/tokens-per-second benchmark (not client HTTP only)',
    'Air-gap and security operator evidence',
])
if live_smoke and not live_rag:
    blockers.append('RAG evaluation failed quality gate (rag_eval.json)')
if live_smoke and not live_rag_bob:
    blockers.append('Bob ACL RAG evaluation failed quality gate (rag_eval_bob_acl.json)')
if live_smoke and not live_load_ok:
    blockers.append('Query load benchmark failed quality gate (load_query.json)')

live_status = 'EXECUTED' if live_smoke else 'NOT_EXECUTED'

record={
  'project':'EAKP Stage 8',
  'generated_utc':datetime.now(timezone.utc).isoformat(),
  'ocr_engine_available':bool(shutil.which('tesseract')),
  'docker_engine_command_available':bool(shutil.which('docker')),
  'compose_yaml_parse':valid_compose,
  'pytest_status':'PASS' if pr.returncode==0 else 'FAIL',
  'pytest_summary':(pr.stdout+pr.stderr)[-1500:],
  'test_scope':'SQLite+HTTP tests with simulated AI/index adapters; actual local Tesseract OCR on synthetic scans',
  'live_qdrant_neo4j_ollama_e2e': live_status,
  'live_ocr_e2e': 'EXECUTED' if live_ocr else 'NOT_EXECUTED',
  'live_rag_eval': 'PASS' if live_rag else 'NOT_EXECUTED',
  'live_rag_bob_acl': 'PASS' if live_rag_bob else 'NOT_EXECUTED',
  'live_load_query_report': 'PASS' if live_load_ok else ('PRESENT' if (reports / 'load_query.json').is_file() else 'MISSING'),
  'air_gap_certification':'NOT_EXECUTED',
  'gpu_inference_benchmark':'NOT_EXECUTED',
  'security_pentest':'NOT_EXECUTED',
  'release_acceptance':'BLOCKED' if blockers else 'ACCEPTED',
  'blockers': blockers,
  'evidence_files': {
    'integration_smoke': str(reports / 'integration_smoke.json') if live_smoke else None,
    'ocr_live_e2e': str(reports / 'ocr_live_e2e.json') if live_ocr else None,
    'load_query': str(reports / 'load_query.json') if live_load_ok else None,
    'rag_eval': str(reports / 'rag_eval.json') if live_rag else None,
    'rag_eval_bob_acl': str(reports / 'rag_eval_bob_acl.json') if live_rag_bob else None,
  },
}
out=root/'reports/stage8_preflight.json'
out.parent.mkdir(parents=True,exist_ok=True)
out.write_text(json.dumps(record,indent=2,ensure_ascii=False),encoding='utf-8')
print(json.dumps(record,indent=2,ensure_ascii=False))
sys.exit(0 if (pr.returncode==0 and valid_compose) else 2)
