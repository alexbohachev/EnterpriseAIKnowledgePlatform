#!/usr/bin/env python3
"""External black-box RAG evaluation against a *running* EAKP instance.

The test set is labeled by a human; this tool DOES NOT validate factuality or
hallucination beyond explicitly supplied expected documents/answer substrings.
Only aggregate results and case IDs are saved, never prompts or model outputs.
"""
from __future__ import annotations
import argparse
from collections import Counter
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import re
import sys
import httpx

REF = re.compile(r'\[S(\d+)\]')


def evaluate_cases(cases: list[dict], ask) -> dict:
    stats = Counter()
    rows = []
    for i, case in enumerate(cases, 1):
        case_id = str(case.get('id', f'case-{i}'))[:64]
        expected = set(case.get('expected_doc_ids', []))
        expected_abstain = case.get('expected_abstain', False)
        required = list(case.get('must_include', []))
        row = {'id': case_id}
        try:
            response = ask(case['question'])
            if isinstance(response, httpx.Response):
                if response.status_code != 200:
                    row['status'] = 'http_error'
                    row['http_status'] = response.status_code
                    stats['failed_requests'] += 1
                    rows.append(row)
                    continue
                response = response.json()
            docs = {c['document_id'] for c in response['citations']}
            expected_labels = {c['source'] for c in response['citations']}
            answer = response['answer']
            cited = {f'S{v}' for v in REF.findall(answer)}
            valid_citations = cited.issubset(expected_labels)
            row['status'] = 'ok'
            row['citation_labels_valid'] = valid_citations
            stats['completed'] += 1
            stats['valid_citation_labels'] += int(valid_citations)
            if expected:
                recall = len(docs & expected) / len(expected)
                row['document_recall'] = round(recall, 4)
                stats['recall_sum'] += recall
                stats['recall_cases'] += 1
            if expected_abstain:
                abstained = not response['citations'] and response['retrieval_count'] == 0
                row['retrieval_abstention_pass'] = abstained
                stats['abstention_correct'] += int(abstained)
                stats['abstention_cases'] += 1
            if required:
                match = all(fragment.casefold() in answer.casefold() for fragment in required)
                row['required_text_pass'] = match
                stats['required_text_correct'] += int(match)
                stats['required_text_cases'] += 1
        except (KeyError, TypeError, ValueError, httpx.HTTPError):
            row['status'] = 'failed_request_or_schema'
            stats['failed_requests'] += 1
        rows.append(row)
    return {
        'cases': len(cases), 'completed': stats['completed'], 'failed': stats['failed_requests'],
        'citation_label_validity': (stats['valid_citation_labels'] / stats['completed'] if stats['completed'] else None),
        'document_recall_at_returned': (round(stats['recall_sum'] / stats['recall_cases'], 4) if stats['recall_cases'] else None),
        'abstention_accuracy': (stats['abstention_correct'] / stats['abstention_cases'] if stats['abstention_cases'] else None),
        'required_text_accuracy': (stats['required_text_correct'] / stats['required_text_cases'] if stats['required_text_cases'] else None),
        'records': rows,
        'limitations': 'Not an automated ground-truth factuality, faithfulness or human safety assessment.'
    }


def load_cases(path: Path) -> list[dict]:
    cases = [json.loads(line) for line in path.read_text(encoding='utf-8').splitlines() if line.strip()]
    if not cases:
        raise ValueError('Empty evaluation set')
    for case in cases:
        if not isinstance(case.get('question'), str) or not case['question'].strip():
            raise ValueError('Every case requires a question')
        if any('REPLACE' in str(x).upper() for x in case.values()):
            raise ValueError('Replace example IDs and expected answers before evaluation')
    return cases


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--dataset', default='examples/eval_template.jsonl')
    p.add_argument('--url', default='http://127.0.0.1:8000')
    p.add_argument('--output', default='reports/rag_eval.json')
    p.add_argument('--timeout', type=float, default=180)
    args = p.parse_args()
    token = os.getenv('EAKP_EVAL_TOKEN')
    if not token:
        p.error('EAKP_EVAL_TOKEN is required (do not paste tokens in commands)')
    cases = load_cases(Path(args.dataset))
    with httpx.Client(base_url=args.url, timeout=args.timeout, trust_env=False) as client:
        def ask(question):
            return client.post('/api/v1/query', headers={'Authorization': f'Bearer {token}'}, json={'question': question})
        result = evaluate_cases(cases, ask)
    result['generated_utc'] = datetime.now(timezone.utc).isoformat()
    result['runtime'] = 'live_http'
    dest = Path(args.output)
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(json.dumps(result, indent=2), encoding='utf-8')
    print(json.dumps({k: v for k, v in result.items() if k != 'records'}, indent=2))
    sys.exit(0 if result['failed'] == 0 else 2)


if __name__ == '__main__':
    main()
