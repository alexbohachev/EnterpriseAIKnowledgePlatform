#!/usr/bin/env python3
"""Real scanned-PDF E2E acceptance. Requires actual local Docker deployment.

Checks OCR -> worker -> vector/graph indexing -> local LLM query.
It does NOT establish security certification or OCR of diagrams/tables.
"""
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
from PIL import Image, ImageDraw, ImageFont
from reportlab.pdfgen.canvas import Canvas
from reportlab.lib.utils import ImageReader


def scanned_fixture() -> bytes:
    im = Image.new('RGB', (1400, 400), 'white')
    font_path = next((p for p in (
        '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',
        '/usr/share/fonts/truetype/liberation2/LiberationSans-Regular.ttf',
        ) if Path(p).is_file()), None)
    font = ImageFont.truetype(font_path, 52) if font_path else ImageFont.load_default()
    ImageDraw.Draw(im).text((50, 120), 'PROJECT ORION-OCR-ACCEPTANCE ONLY.',
                             font=font, fill='black')
    ImageDraw.Draw(im).text((50, 200), 'Launch date 12 June 2032.',
                             font=font, fill='black')
    buff = BytesIO()
    pdf = Canvas(buff, pagesize=(650,260))
    pdf.drawImage(ImageReader(im), 0, 0, width=650, height=260)
    pdf.showPage()
    pdf.save()
    return buff.getvalue()


def _must(response, expected):
    if response.status_code != expected:
        raise RuntimeError(f'Expected HTTP {expected}; got {response.status_code}')
    return response.json() if response.content else None


def run(base_url: str, email: str, pwd: str, wait_seconds=240):
    evidence = []
    with httpx.Client(base_url=base_url, timeout=180, trust_env=False) as client:
        token = _must(client.post('/api/v1/auth/token',
                    json={'email':email,'password':pwd}), 200)['access_token']
        auth = {'Authorization':f'Bearer {token}'}
        up = _must(client.post('/api/v1/documents', headers=auth,
              data={'title':'Synthetic OCR acceptance', 'classification':'confidential'},
              files={'file':('synthetic-scanned.pdf',scanned_fixture(),'application/pdf')}), 202)
        evidence.append('scanned_pdf_upload:passed')
        deadline = time.monotonic() + wait_seconds
        last = None
        while time.monotonic() < deadline:
            last = _must(client.get(f'/api/v1/jobs/{up["job_id"]}', headers=auth),200)['status']
            if last == 'INDEXED':
                evidence.append('scanned_pdf_ocr_and_dual_index:passed')
                break
            if last in ('FAILED','NEEDS_OCR','INDEX_FAILED'):
                raise RuntimeError('OCR/indexing did not complete: ' + last)
            time.sleep(3)
        if last != 'INDEXED':
            raise RuntimeError('OCR/indexing timeout; last status: '+str(last))
        question = 'What is the launch date of Project ORION-OCR-ACCEPTANCE ONLY?'
        doc_id = up['document_id']
        cited = False
        for attempt in range(5):
            if attempt:
                time.sleep(2)
            answer = _must(client.post('/api/v1/query', headers=auth,
                  json={'question': question}), 200)
            if doc_id in {c['document_id'] for c in answer.get('citations', [])}:
                cited = True
                break
        if not cited:
            raise RuntimeError(
                f'OCR document {doc_id} not cited; citations={answer.get("citations", [])}'
            )
        evidence.append('scanned_document_has_citation:passed')
    return {'scenario':'real_local_ocr_e2e','passed':True,'events':evidence,
            'generated_utc':datetime.now(timezone.utc).isoformat(),
            'limitations':'OCR/date correctness and image understanding require human assessment; not an air-gap or multi-user authorization proof'}


def main():
    p=argparse.ArgumentParser()
    p.add_argument('--url',default='http://127.0.0.1:8000')
    p.add_argument('--max-wait-seconds',type=int,default=240)
    p.add_argument('--accept-synthetic-write',action='store_true')
    p.add_argument('--output',default='reports/ocr_live_e2e.json')
    args=p.parse_args()
    if not args.accept_synthetic_write:
        p.error('Explicit --accept-synthetic-write required for disposable test environment')
    email=os.getenv('EAKP_TEST_ALICE_EMAIL')
    pwd=os.getenv('EAKP_TEST_ALICE_PASSWORD')
    if not email or not pwd:
        p.error('Set EAKP_TEST_ALICE_EMAIL and EAKP_TEST_ALICE_PASSWORD in environment')
    res=run(args.url,email,pwd,args.max_wait_seconds)
    path=Path(args.output)
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(res,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(res,ensure_ascii=False,indent=2))

if __name__=='__main__':
    main()
