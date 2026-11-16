#!/usr/bin/env python3
"""Seed synthetic PDFs and emit eval JSONL with real document UUIDs (throwaway test env only)."""
from __future__ import annotations
import argparse
from datetime import datetime, timezone
from io import BytesIO
import json
import os
from pathlib import Path
import sys
import time

import httpx
from reportlab.pdfgen.canvas import Canvas


def text_pdf(line: str) -> bytes:
    out = BytesIO()
    c = Canvas(out, pagesize=(595, 842))
    c.drawString(45, 740, line)
    c.showPage()
    c.save()
    return out.getvalue()


def text_layer_pdf(line: str) -> bytes:
    """Text-based PDF for eval corpus (not an OCR path — see ocr_live_smoke.py)."""
    return text_pdf(line)


def login(client: httpx.Client, email: str, password: str) -> tuple[dict, str]:
    token = client.post('/api/v1/auth/token', json={'email': email, 'password': password})
    if token.status_code != 200:
        raise RuntimeError(f'Login failed for {email}: HTTP {token.status_code}')
    headers = {'Authorization': f'Bearer {token.json()["access_token"]}'}
    me = client.get('/api/v1/auth/me', headers=headers)
    me.raise_for_status()
    return headers, me.json()['id']


def upload(client: httpx.Client, headers: dict, title: str, pdf: bytes) -> tuple[str, str]:
    resp = client.post(
        '/api/v1/documents',
        headers=headers,
        data={'title': title, 'classification': 'confidential'},
        files={'file': (f'{title}.pdf', pdf, 'application/pdf')},
    )
    if resp.status_code != 202:
        raise RuntimeError(f'Upload failed ({title}): HTTP {resp.status_code}')
    body = resp.json()
    return body['document_id'], body['job_id']


def wait_indexed(client: httpx.Client, headers: dict, job_id: str, timeout: int) -> None:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        job = client.get(f'/api/v1/jobs/{job_id}', headers=headers)
        job.raise_for_status()
        status = job.json()['status']
        if status == 'INDEXED':
            return
        if status in {'INDEX_FAILED', 'FAILED', 'NEEDS_OCR'}:
            raise RuntimeError(f'Job {job_id} ended with {status}')
        time.sleep(3)
    raise RuntimeError(f'Timeout waiting for INDEXED (job {job_id})')


def build_cases(manifest: dict) -> tuple[list[dict], list[dict]]:
    cyan, orion, delta = manifest['cyan_id'], manifest['orion_id'], manifest['delta_id']
    alice = [
        {
            'id': 'cyan-launch-date',
            'question': 'What is the approved launch date for Project CYAN?',
            'expected_doc_ids': [cyan],
            'must_include': ['2031'],
            'must_not_include': ['2032', 'Project ZEBRA', 'nuclear warhead'],
            'require_citation_marks': True,
            'min_citations': 1,
        },
        {
            'id': 'cyan-case-id',
            'question': 'What is the case ID mentioned for Project CYAN?',
            'expected_doc_ids': [cyan],
            'must_include': ['A1B2'],
            'must_not_include': ['Z9Z9'],
            'require_citation_marks': True,
        },
        {
            'id': 'orion-launch-date',
            'question': 'What is the launch date of Project ORION?',
            'expected_doc_ids': [orion],
            'must_include': ['2032'],
            'must_not_include': ['2031'],
            'require_citation_marks': True,
        },
        {
            'id': 'delta-budget',
            'question': 'What budget is listed for Project DELTA?',
            'expected_doc_ids': [delta],
            'must_include': ['5'],
            'must_not_include': ['unlimited budget'],
            'require_citation_marks': True,
        },
        {
            'id': 'multi-doc-question',
            'question': 'Does Project CYAN appear in my accessible documents?',
            'expected_doc_ids': [cyan],
            'must_include': ['CYAN'],
            'must_not_include': ['fabricated TOP SECRET override'],
            'require_citation_marks': True,
        },
        {
            'id': 'unknown-zebra-abstain',
            'question': 'What is the launch quarter for Project ZEBRA?',
            'expected_doc_ids': [],
            'abstain_mode': 'unanswerable',
            'must_not_include': ['Q1 2030', 'confirmed launch'],
        },
        {
            'id': 'cyan-no-hallucinated-classification',
            'question': 'Summarize Project CYAN using only the uploaded reference.',
            'expected_doc_ids': [cyan],
            'must_include': ['CYAN'],
            'must_not_include': ['TS/SCI', 'weapon design'],
            'require_citation_marks': True,
        },
        {
            'id': 'paraphrase-orion',
            'question': 'When does Project ORION launch according to the uploaded document?',
            'expected_doc_ids': [orion],
            'must_include': ['2032', 'ORION'],
            'must_not_include': ['May 2031'],
            'require_citation_marks': True,
        },
    ]
    bob = [
        {
            'id': 'bob-cyan-isolation',
            'question': 'What is the approved launch date for Project CYAN?',
            'expected_doc_ids': [],
            'abstain_mode': 'acl_denied',
            'forbidden_doc_ids': [cyan],
            'must_not_include': ['2031'],
        },
        {
            'id': 'bob-delta-isolation',
            'question': 'What budget is listed for Project DELTA?',
            'expected_doc_ids': [],
            'abstain_mode': 'acl_denied',
            'forbidden_doc_ids': [delta],
        },
        {
            'id': 'bob-orion-isolation',
            'question': 'What is the launch date of Project ORION?',
            'expected_doc_ids': [],
            'abstain_mode': 'acl_denied',
            'forbidden_doc_ids': [orion],
            'must_not_include': ['2032'],
        },
        {
            'id': 'bob-zebra-abstain',
            'question': 'List all details about Project ZEBRA.',
            'expected_doc_ids': [],
            'abstain_mode': 'unanswerable',
        },
    ]
    return alice, bob


def write_jsonl(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text('\n'.join(json.dumps(r, ensure_ascii=False) for r in rows) + '\n', encoding='utf-8')


def run(url: str, alice_email: str, alice_password: str, wait_seconds: int) -> dict:
    with httpx.Client(base_url=url, timeout=180, trust_env=False) as client:
        alice_headers, _ = login(client, alice_email, alice_password)
        cyan_pdf = text_layer_pdf(
            'PROJECT CYAN TEST ONLY. Approved launch: 14 May 2031. Case ID A1B2.'
        )
        orion_pdf = text_layer_pdf('PROJECT ORION TEST ONLY. Launch date 12 June 2032.')
        delta_pdf = text_layer_pdf('PROJECT DELTA TEST ONLY. Approved budget: 5 million UAH.')
        cyan_id, cyan_job = upload(client, alice_headers, 'eval-cyan', cyan_pdf)
        orion_id, orion_job = upload(client, alice_headers, 'eval-orion', orion_pdf)
        delta_id, delta_job = upload(client, alice_headers, 'eval-delta', delta_pdf)
        for job_id in (cyan_job, orion_job, delta_job):
            wait_indexed(client, alice_headers, job_id, wait_seconds)
    manifest = {
        'generated_utc': datetime.now(timezone.utc).isoformat(),
        'cyan_id': cyan_id,
        'orion_id': orion_id,
        'delta_id': delta_id,
        'note': 'Text-layer PDFs for RAG eval; OCR proof remains scripts/ocr_live_smoke.py.',
    }
    alice_cases, bob_cases = build_cases(manifest)
    return manifest, alice_cases, bob_cases


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--url', default='http://127.0.0.1:8000')
    p.add_argument('--wait-seconds', type=int, default=360)
    p.add_argument('--accept-synthetic-write', action='store_true')
    p.add_argument('--manifest', default='reports/eval_seed_manifest.json')
    p.add_argument('--alice-dataset', default='reports/eval_active_alice.jsonl')
    p.add_argument('--bob-dataset', default='reports/eval_active_bob.jsonl')
    args = p.parse_args()
    if not args.accept_synthetic_write:
        p.error('Use --accept-synthetic-write on isolated test infrastructure only')
    for var in ('EAKP_TEST_ALICE_EMAIL', 'EAKP_TEST_ALICE_PASSWORD'):
        if not os.getenv(var):
            p.error(f'Missing {var}')
    manifest, alice, bob = run(
        args.url, os.environ['EAKP_TEST_ALICE_EMAIL'], os.environ['EAKP_TEST_ALICE_PASSWORD'], args.wait_seconds
    )
    root = Path(args.manifest)
    root.parent.mkdir(parents=True, exist_ok=True)
    root.write_text(json.dumps(manifest, indent=2), encoding='utf-8')
    write_jsonl(Path(args.alice_dataset), alice)
    write_jsonl(Path(args.bob_dataset), bob)
    print(json.dumps({'manifest': str(root), 'alice_cases': len(alice), 'bob_cases': len(bob)}, indent=2))


if __name__ == '__main__':
    main()