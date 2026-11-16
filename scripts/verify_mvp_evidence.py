#!/usr/bin/env python3
"""Verify reports/ before bundling or uploading a GitHub release ZIP."""
from __future__ import annotations
import json
import subprocess
import sys
from pathlib import Path

from mvp_evidence_gates import EVIDENCE_BUNDLE_SCHEMA_VERSION, assess_mvp


def git_head(root: Path) -> str | None:
    proc = subprocess.run(
        ['git', 'rev-parse', 'HEAD'],
        cwd=root,
        capture_output=True,
        text=True,
        timeout=30,
    )
    return proc.stdout.strip() if proc.returncode == 0 else None


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    reports = root / 'reports'
    mvp_status, blockers = assess_mvp(reports)
    head = git_head(root)
    preflight_path = reports / 'stage8_preflight.json'
    preflight_commit = None
    if preflight_path.is_file():
        try:
            preflight_commit = json.loads(preflight_path.read_text(encoding='utf-8')).get('git_commit')
        except (json.JSONDecodeError, OSError):
            pass
    alignment_ok = not head or not preflight_commit or preflight_commit == head
    payload = {
        'evidence_bundle_schema_version': EVIDENCE_BUNDLE_SCHEMA_VERSION,
        'git_head': head,
        'preflight_git_commit': preflight_commit,
        'code_report_alignment': 'PASS' if alignment_ok else 'MISMATCH',
        'mvp_acceptance': mvp_status,
        'mvp_blockers': blockers,
    }
    print(json.dumps(payload, indent=2))
    if mvp_status != 'PASS':
        return 2
    if not alignment_ok:
        return 3
    return 0


if __name__ == '__main__':
    sys.exit(main())