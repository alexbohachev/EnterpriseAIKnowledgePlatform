"""Stage 6 observability tests; assertions are deterministic, no external services."""
from __future__ import annotations
import importlib.util
import json
import sys
from pathlib import Path
import pytest
from prometheus_client.parser import text_string_to_metric_families
from app.config import Settings
from app.observability import Observability, safe_route

TOKEN = 'local-metrics-secret-12345-abcdefXYZ98765'


def parse(body):
    return list(text_string_to_metric_families(body.decode()))


def samples(body, key):
    return [s for f in parse(body) for s in f.samples if s.name == key]


def test_metrics_404_when_disabled_by_default(context):
    c = context['client']
    assert c.get('/internal/metrics').status_code == 404
    assert c.get('/internal/metrics', headers={'Authorization':'Bearer anything'}).status_code == 404


def test_metrics_bearer_secret_required_and_request_labels_are_templates(context, tokens):
    c = context['client']
    context['settings'].metrics_token = TOKEN
    path = f"/api/v1/documents/{'a' * 36}"
    r = c.get(path, headers=tokens['alice'])
    assert r.status_code == 404
    assert c.get('/internal/metrics').status_code == 403
    assert c.get('/internal/metrics', headers={'Authorization': 'Bearer wrong'}).status_code == 403
    metrics = c.get('/internal/metrics', headers={'Authorization': f'Bearer {TOKEN}'})
    assert metrics.status_code == 200
    assert metrics.headers['content-type'].startswith('text/plain')
    assert 'eakp_http_requests_total' in metrics.text
    # Authenticated dynamic UUID is not emitted as a label value.
    assert 'a' * 36 not in metrics.text
    assert '/api/v1/documents/{document_id}' in metrics.text
    route_samples = samples(metrics.content, 'eakp_http_requests_total')
    assert any(s.labels.get('route') == '/api/v1/documents/{document_id}' and
               s.labels.get('status_class') == '4xx' for s in route_samples)
    assert all('email' not in s.labels and 'user' not in s.labels for s in route_samples)
    # No repeated /metrics scrapes should inflate own metrics.
    previous = metrics.text.count('route="/internal/metrics"')
    assert previous == 0


def test_observer_stage_metrics_bound_names_and_failures():
    obs = Observability()
    with obs.stage('retrieval'):
        obs.rag_excerpts.observe(3)
    with pytest.raises(RuntimeError):
        with obs.stage('generation'):
            raise RuntimeError('test failure')
    with pytest.raises(ValueError):
        with obs.stage('document:secret-token'):
            pass
    names = [(s.name, s.labels) for f in parse(obs.render()) for s in f.samples]
    assert ('eakp_rag_stage_duration_seconds_count', {'stage': 'generation', 'outcome': 'error'}) in names
    assert ('eakp_rag_stage_duration_seconds_count', {'stage': 'retrieval', 'outcome': 'ok'}) in names
    assert all('secret-token' not in str(x) for x in names)


def test_http_request_labels_do_not_store_raw_paths():
    assert safe_route('/api/v1/documents/{document_id}') == '/api/v1/documents/{document_id}'
    assert safe_route('/api/v1/documents/6a536d26-3012-4bdd-a8c4-2e12a471a556') == 'unmatched'
    assert safe_route('/api/v1/query?question=secret') == 'unmatched'
    assert safe_route('/a/'+'k'*200) == 'unmatched'


def test_invalid_metrics_secret_and_external_collector_rejected():
    with pytest.raises(ValueError):
        Settings(jwt_secret='local-test-superrandom-123abc456X987', metrics_token='short')
    with pytest.raises(ValueError):
        Settings(jwt_secret='local-test-superrandom-123abc456X987',
                 otlp_traces_endpoint='https://public.example.org/v1/traces')
    cfg = Settings(jwt_secret='local-test-superrandom-123abc456X987',
                   otlp_traces_endpoint='http://otel-collector:4318/v1/traces')
    assert cfg.otlp_traces_endpoint.startswith('http://otel-collector')


def load_script(name):
    scripts = Path(__file__).resolve().parents[1] / 'scripts'
    scripts_str = str(scripts)
    if scripts_str not in sys.path:
        sys.path.insert(0, scripts_str)
    p = scripts / name
    spec = importlib.util.spec_from_file_location(f'test_{name[:-3]}_script', p)
    obj = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(obj)
    return obj


def test_rag_evaluation_uses_only_explicit_ground_truth_not_guessing():
    script = load_script('evaluate_rag.py')
    cases = [
        {'id': 'citation', 'question':'When?', 'expected_doc_ids':['doc1'], 'must_include':['Wednesday']},
        {'id': 'abstain', 'question':'Secret?', 'abstain_mode': 'unanswerable'},
    ]
    def fake_ask(question):
        return ({'answer':'Wednesday [S1]', 'retrieval_count':1,
                 'citations':[{'source':'S1','document_id':'doc1'}]} if question == 'When?' else
                {'answer':'У доступних документах немає підтвердженої відповіді.','retrieval_count':2,
                 'citations':[]})
    data = script.evaluate_cases(cases, fake_ask)
    assert data['completed'] == 2
    assert data['failed'] == 0
    assert data['document_recall_at_returned'] == 1
    assert data['abstention_accuracy'] == 1
    assert data['citation_label_validity'] == 1
    assert data['quality_failures'] == 0
    assert data['quality_pass_rate'] == 1
    assert 'human factuality review' in data['limitations']


def test_rag_evaluation_unanswerable_allows_retrieval_without_empty_violation():
    script = load_script('evaluate_rag.py')
    case = {'id': 'zebra', 'question': 'ZEBRA?', 'abstain_mode': 'unanswerable',
            'must_not_include': ['Q1 2030']}
    data = script.evaluate_cases([case], lambda _: {
        'answer': 'Немає підтвердженої інформації про ZEBRA у доступних документах.',
        'retrieval_count': 4,
        'citations': [{'source': 'S1', 'document_id': 'other'}],
    })
    assert data['quality_failures'] == 0
    assert data['eval_schema_version'] == 2


def test_assess_mvp_does_not_require_preflight_json(tmp_path):
    gates = load_script('mvp_evidence_gates.py')
    status, blockers = gates.assess_mvp(tmp_path)
    assert status == 'BLOCKED'
    assert not any('stage8_preflight' in b for b in blockers)
    (tmp_path / 'integration_smoke.json').write_text('{"passed": true}', encoding='utf-8')
    (tmp_path / 'ocr_live_e2e.json').write_text('{"passed": true}', encoding='utf-8')
    rag = {
        'eval_schema_version': 2,
        'quality_failures': 0,
        'quality_pass_rate': 1.0,
        'faithfulness_pass_rate': 1.0,
        'completed': 1,
        'failed': 0,
    }
    (tmp_path / 'rag_eval.json').write_text(json.dumps(rag), encoding='utf-8')
    (tmp_path / 'rag_eval_bob_acl.json').write_text(json.dumps(rag), encoding='utf-8')
    load = {
        'report_schema_version': 1,
        'mode': 'query',
        'http_success_ratio': 0.99,
        'latency_ms': {'p95': 100.0},
        'provenance': 'live_http_client_side',
    }
    (tmp_path / 'load_query.json').write_text(json.dumps(load), encoding='utf-8')
    status2, blockers2 = gates.assess_mvp(tmp_path)
    assert status2 == 'PASS'
    assert blockers2 == []


def test_alignment_status_requires_both_git_shas():
    verify = load_script('verify_mvp_evidence.py')
    ok, errs = verify.alignment_status(None, 'abc', True)
    assert not ok and 'git HEAD unavailable' in errs
    ok, errs = verify.alignment_status('abc', None, False)
    assert not ok and any('missing' in e for e in errs)
    ok, errs = verify.alignment_status('abc', None, True)
    assert not ok and 'missing git_commit' in errs[0]
    ok, errs = verify.alignment_status('abc', 'def', True)
    assert not ok and 'does not match' in errs[0]
    ok, errs = verify.alignment_status('abc', 'abc', True)
    assert ok and errs == []


def test_rag_evaluation_unanswerable_rejects_fabricated_answer_without_refusal():
    script = load_script('evaluate_rag.py')
    case = {'id': 'zebra', 'question': 'ZEBRA?', 'abstain_mode': 'unanswerable'}
    data = script.evaluate_cases([case], lambda _: {
        'answer': 'Project ZEBRA will launch next summer with full funding.',
        'retrieval_count': 0,
        'citations': [],
    })
    assert data['quality_failures'] == 1


def test_rag_evaluation_acl_denied_detects_citation_leak():
    script = load_script('evaluate_rag.py')
    case = {'id': 'bob', 'question': 'CYAN?', 'abstain_mode': 'acl_denied',
            'forbidden_doc_ids': ['secret-doc']}
    leak = script.evaluate_cases([case], lambda _: {
        'answer': 'No access',
        'retrieval_count': 1,
        'citations': [{'source': 'S1', 'document_id': 'secret-doc'}],
    })
    assert leak['quality_failures'] == 1


def test_rag_evaluation_faithfulness_forbidden_text_and_citation_marks():
    script = load_script('evaluate_rag.py')
    case = {
        'id': 'faith',
        'question': 'When?',
        'expected_doc_ids': ['doc1'],
        'must_include': ['2031'],
        'must_not_include': ['2032'],
        'require_citation_marks': True,
        'min_citations': 1,
    }
    ok = script.evaluate_cases([case], lambda _: {
        'answer': 'Launch 2031 [S1]',
        'retrieval_count': 1,
        'citations': [{'source': 'S1', 'document_id': 'doc1'}],
    })
    assert ok['faithfulness_pass_rate'] == 1
    bad = script.evaluate_cases([case], lambda _: {
        'answer': 'Wrong 2032 [S1]',
        'retrieval_count': 1,
        'citations': [{'source': 'S1', 'document_id': 'doc1'}],
    })
    assert bad['faithfulness_pass_rate'] == 0
    assert bad['quality_failures'] == 1


def test_rag_evaluation_detects_unsupported_citation_label():
    script = load_script('evaluate_rag.py')
    data = script.evaluate_cases([{'id':'bad','question':'Check','expected_doc_ids':['doc1']}],
        lambda _: {'answer':'Found [S99]','retrieval_count':1,
                   'citations':[{'source':'S1','document_id':'doc2'}]})
    assert data['citation_label_validity'] == 0
    assert data['document_recall_at_returned'] == 0
    assert data['quality_failures'] == 1
    assert data['quality_pass_rate'] == 0


def test_client_load_summary_and_nearest_rank_percentiles():
    script = load_script('load_test.py')
    assert script.percentile([1,3,9,11,5], .95) == 11
    report = script.summarize(2., [(10.,200),(20.,500),(30.,429),(40.,'transport_error')], 'health')
    assert report['requests'] == 4
    assert report['requests_per_second'] == 2
    assert report['http_success_ratio'] == .25
    assert report['status_counts']['500'] == 1
    assert report['latency_ms']['p95'] == 40


def test_compose_ollama_network_regression_and_no_public_monitoring_bindings():
    # No Docker daemon available here: static safety assertions, NOT deployment validation.
    yaml = pytest.importorskip('yaml')
    data = yaml.safe_load((Path(__file__).resolve().parents[1] / 'compose.yaml').read_text())
    services = data['services']
    assert 'backend' in services['ollama']['networks']
    assert 'monitoring' in services['prometheus']['profiles']
    assert services['prometheus']['ports'] == ['127.0.0.1:9090:9090']
    assert services['grafana']['ports'] == ['127.0.0.1:3000:3000']
    assert services['jaeger']['ports'] == ['127.0.0.1:16686:16686']
