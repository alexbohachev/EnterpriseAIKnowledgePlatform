#!/usr/bin/env bash
# Відтворюване синтетичне демо EAKP (Linux/macOS). Лише throwaway-стенд.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

command -v docker >/dev/null || { echo 'Docker required' >&2; exit 1; }

if [[ ! -f .env ]]; then
  cp .env.example .env
  echo 'Created .env — set secrets locally' >&2
fi

set -a
# shellcheck disable=SC1091
source scripts/demo_env.example
set +a

docker compose -f compose.yaml -f compose.dev.yaml up -d --build
docker compose exec -T api python -m app.integration_probe

create_user() {
  local email=$1 pw=$2 out
  set +e
  out="$(printf '%s' "$pw" | docker compose exec -T api python -m app.cli create-user \
    --email "$email" --password-stdin 2>&1)"
  local code=$?
  set -e
  if [[ $code -ne 0 && "$out" != *"already exists"* ]]; then
    echo "$out" >&2
    exit "$code"
  fi
}
create_user alice@test.local "$EAKP_TEST_ALICE_PASSWORD"
create_user bob@test.local "$EAKP_TEST_BOB_PASSWORD"

python scripts/integration_smoke.py --accept-synthetic-write --url http://127.0.0.1:8000
python scripts/ocr_live_smoke.py --accept-synthetic-write --url http://127.0.0.1:8000
python scripts/seed_synthetic_eval_corpus.py --accept-synthetic-write --url http://127.0.0.1:8000

alice_tok="$(curl -fsS -H 'Content-Type: application/json' \
  -d "{\"email\":\"alice@test.local\",\"password\":\"$EAKP_TEST_ALICE_PASSWORD\"}" \
  http://127.0.0.1:8000/api/v1/auth/token | python -c 'import json,sys; print(json.load(sys.stdin)["access_token"])')"
export EAKP_EVAL_TOKEN="$alice_tok"
python scripts/evaluate_rag.py --dataset reports/eval_active_alice.jsonl --output reports/rag_eval.json

bob_tok="$(curl -fsS -H 'Content-Type: application/json' \
  -d "{\"email\":\"bob@test.local\",\"password\":\"$EAKP_TEST_BOB_PASSWORD\"}" \
  http://127.0.0.1:8000/api/v1/auth/token | python -c 'import json,sys; print(json.load(sys.stdin)["access_token"])')"
export EAKP_EVAL_TOKEN="$bob_tok"
python scripts/evaluate_rag.py --dataset reports/eval_active_bob.jsonl --output reports/rag_eval_bob_acl.json

export EAKP_EVAL_TOKEN="$alice_tok"
python scripts/load_test.py --mode query --accept-real-load --seconds 20 --rps 1 \
  --output reports/load_query.json --url http://127.0.0.1:8000

export EAKP_REQUIRE_MVP_LIVE=1
python scripts/stage8_preflight.py --require-mvp-live
python scripts/open_requirements_register.py

echo "Done. Artifacts under reports/"