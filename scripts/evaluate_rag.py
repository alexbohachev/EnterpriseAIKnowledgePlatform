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


def score_faithfulness(row: dict, case: dict, response: dict, answer: str) -> None:
    forbidden = list(case.get('must_not_include') or [])
    row['forbidden_text_absent'] = all(f.casefold() not in answer.casefold() for f in forbidden)
    min_citations = int(case.get('min_citations') or 0)
    if case.get('require_citations_when_answered') and not case.get('expected_abstain'):
        min_citations = max(min_citations, 1)
    citation_count = len(response.get('citations') or [])
    row['min_citations_pass'] = citation_count >= min_citations
    row['citation_marks_present'] = (
        not case.get('require_citation_marks')
        or not response.get('citations')
        or bool(REF.search(answer))
    )
    row['faithfulness_pass'] = (
        row['forbidden_text_absent']
        and row['min_citations_pass']
        and row['citation_marks_present']
    )


def case_quality_pass(row: dict, case: dict) -> bool:
    if row.get('status') != 'ok':
        return False
    if row.get('citation_labels_valid') is False:
        return False
    if row.get('faithfulness_pass') is False:
        return False
    expected = set(case.get('expected_doc_ids') or [])
    if expected and row.get('document_recall', 0) < 1.0:
        return False
    if case.get('expected_abstain') and not row.get('retrieval_abstention_pass'):
        return False
    if case.get('must_include') and not row.get('required_text_pass'):
        return False
    return True


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
            score_faithfulness(row, case, response, answer)
            stats['faithfulness_correct'] += int(row['faithfulness_pass'])
            stats['faithfulness_cases'] += 1
            row['quality_pass'] = case_quality_pass(row, case)
            if not row['quality_pass']:
                stats['quality_failures'] += 1
        except (KeyError, TypeError, ValueError, httpx.HTTPError):
            row['status'] = 'failed_request_or_schema'
            stats['failed_requests'] += 1
            stats['quality_failures'] += 1
        rows.append(row)
    return {
        'cases': len(cases), 'completed': stats['completed'], 'failed': stats['failed_requests'],
        'quality_failures': stats['quality_failures'],
        'quality_pass_rate': (
            round((stats['completed'] - stats['quality_failures']) / stats['completed'], 4)
            if stats['completed'] else None
        ),
        'citation_label_validity': (stats['valid_citation_labels'] / stats['completed'] if stats['completed'] else None),
        'document_recall_at_returned': (round(stats['recall_sum'] / stats['recall_cases'], 4) if stats['recall_cases'] else None),
        'abstention_accuracy': (stats['abstention_correct'] / stats['abstention_cases'] if stats['abstention_cases'] else None),
        'required_text_accuracy': (stats['required_text_correct'] / stats['required_text_cases'] if stats['required_text_cases'] else None),
        'faithfulness_pass_rate': (
            round(stats['faithfulness_correct'] / stats['faithfulness_cases'], 4)
            if stats['faithfulness_cases'] else None
        ),
        'records': rows,
        'limitations': (
            'Checks operator-supplied must_include/must_not_include, citation marks and abstain rules. '
            'Not a substitute for human factuality review or adversarial red teaming.'
        ),
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
    p.add_argument('--min-quality-pass-rate', type=float, default=1.0)
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
    quality_ok = (
        result.get('quality_pass_rate') is not None
        and result['quality_pass_rate'] >= args.min_quality_pass_rate
    )
    sys.exit(0 if result['failed'] == 0 and quality_ok else 2)


if __name__ == '__main__':
    main()
