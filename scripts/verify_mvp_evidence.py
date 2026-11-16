#!/usr/bin/env python3
"""Verify reports/ before bundling or uploading a GitHub release ZIP."""
from __future__ import annotations
import json
import subprocess
import sys
from pathlib import Path

from mvp_evidence_gates import EVIDENCE_BUNDLE_SCHEMA_VERSION, assess_mvp


def alignment_status(
    head: str | None,
    preflight_commit: str | None,
    preflight_exists: bool,
) -> tuple[bool, list[str]]:
    errors: list[str] = []
    if not head:
        errors.append('git HEAD unavailable')
    if not preflight_exists:
        errors.append('stage8_preflight.json missing (run stage8_preflight.py after demo)')
    elif not preflight_commit:
        errors.append('stage8_preflight.json missing git_commit')
    elif head and preflight_commit != head:
        errors.append('preflight git_commit does not match HEAD')
    return (not errors, errors)


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
    preflight_exists = preflight_path.is_file()
    if preflight_exists:
        try:
            preflight_commit = json.loads(preflight_path.read_text(encoding='utf-8')).get('git_commit')
        except (json.JSONDecodeError, OSError):
            preflight_commit = None
    alignment_ok, alignment_errors = alignment_status(head, preflight_commit, preflight_exists)
    payload = {
        'evidence_bundle_schema_version': EVIDENCE_BUNDLE_SCHEMA_VERSION,
        'git_head': head,
        'preflight_git_commit': preflight_commit,
        'code_report_alignment': 'PASS' if alignment_ok else 'MISMATCH',
        'alignment_errors': alignment_errors,
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