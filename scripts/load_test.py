#!/usr/bin/env python3
"""Client-side HTTP load probe with request-rate ceiling and explicit report provenance.

This is NOT a substitute for multi-client distributed load testing. All metrics
are client-observed; performance cannot be reported without actually executing it.
"""
from __future__ import annotations
import argparse
import asyncio
from collections import Counter
from datetime import datetime, timezone
import json
import math
import os
from pathlib import Path
import time
import httpx


def percentile(sample: list[float], fraction: float) -> float | None:
    if not sample:
        return None
    s = sorted(sample)
    return round(s[max(0, min(len(s) - 1, math.ceil(len(s) * fraction) - 1))], 4)


def summarize(elapsed: float, measurements: list[tuple[float, int | str]], mode: str) -> dict:
    counts = Counter(str(status) for _, status in measurements)
    latencies = [elapsed for elapsed, _ in measurements]
    ok = sum(n for k, n in counts.items() if k.startswith('2'))
    total = len(measurements)
    return {'mode': mode, 'elapsed_seconds': round(elapsed, 3), 'requests': total,
            'status_counts': dict(sorted(counts.items())),
            'requests_per_second': round(total / max(elapsed, 1e-9), 3),
            'successes_per_second': round(ok / max(elapsed, 1e-9), 3),
            'http_success_ratio': round(ok / total, 4) if total else None,
            'latency_ms': {'p50': percentile(latencies, .5), 'p95': percentile(latencies, .95),
                           'p99': percentile(latencies, .99)},
            'note': 'Client-side HTTP metrics; includes 4xx, 5xx and timeouts. Not GPU tokens/sec or true user concurrency.'}


async def run_load(url: str, mode: str, token: str | None, duration: float, concurrency: int,
                   rate: float, question: str, max_requests: int = 20000) -> dict:
    if mode == 'query' and not token:
        raise ValueError('EAKP_EVAL_TOKEN required for query mode')
    if not (0 < rate <= 25 and 0 < concurrency <= 64 and 0 < duration <= 600):
        raise ValueError('Bounded load requires 0 < rate <= 25 RPS, 1..64 workers, <= 600s')
    measurements = []
    next_slot = [time.perf_counter()]
    issued = [0]
    lock = asyncio.Lock()
    started = time.perf_counter()
    deadline = started + duration
    headers = {'Authorization': f'Bearer {token}'} if token else {}
    timeout = httpx.Timeout(60 if mode == 'query' else 8)
    async with httpx.AsyncClient(base_url=url, trust_env=False, timeout=timeout) as client:
        async def worker():
            while True:
                async with lock:
                    now = time.perf_counter()
                    if now >= deadline or issued[0] >= max_requests:
                        return
                    due = max(next_slot[0], now)
                    if due >= deadline:
                        return
                    next_slot[0] = due + 1.0 / rate
                    issued[0] += 1
                await asyncio.sleep(max(0, due - time.perf_counter()))
                t0 = time.perf_counter()
                try:
                    if mode == 'query':
                        resp = await client.post('/api/v1/query', headers=headers, json={'question': question})
                    else:
                        resp = await client.get('/healthz')
                    status = resp.status_code
                except httpx.HTTPError:
                    status = 'transport_error'
                measurements.append(((time.perf_counter() - t0) * 1000, status))
        await asyncio.gather(*(worker() for _ in range(concurrency)))
    elapsed = time.perf_counter() - started
    return summarize(elapsed, measurements, mode)


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--mode', choices=['query', 'health'], default='query')
    p.add_argument('--url', default='http://127.0.0.1:8000')
    p.add_argument('--seconds', type=float, default=15)
    p.add_argument('--concurrency', type=int, default=2)
    p.add_argument('--rps', type=float, default=1)
    p.add_argument('--question', default='What is the status described by my accessible documents?')
    p.add_argument('--accept-real-load', action='store_true', help='Required for AI queries; check load against rate limiting')
    p.add_argument('--output', default='reports/load_results.json')
    args = p.parse_args()
    if args.mode == 'query' and not args.accept_real_load:
        p.error('For query mode supply --accept-real-load after reviewing rate-limit costs and test infrastructure')
    result = asyncio.run(run_load(args.url, args.mode, os.getenv('EAKP_EVAL_TOKEN'),
                                  args.seconds, args.concurrency, args.rps, args.question))
    result.update({
        'report_schema_version': 1,
        'generated_utc': datetime.now(timezone.utc).isoformat(),
        'provenance': 'live_http_client_side',
        'configured_rps': args.rps,
        'concurrency': args.concurrency,
    })
    dest = Path(args.output)
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(json.dumps(result, indent=2), encoding='utf-8')
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
