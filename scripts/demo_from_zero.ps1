#Requires -Version 5.1
# Відтворюване синтетичне демо EAKP (Windows). Лише throwaway-стенд.
$ErrorActionPreference = 'Stop'
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root

if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
    throw 'Docker CLI not found'
}

$EnvFile = Join-Path $Root 'scripts\demo_env.example'
if (-not (Test-Path (Join-Path $Root '.env'))) {
    Copy-Item (Join-Path $Root '.env.example') (Join-Path $Root '.env')
    Write-Warning 'Created .env from .env.example — set secrets before production-like runs.'
}

Get-Content $EnvFile | ForEach-Object {
    if ($_ -match '^\s*#' -or $_ -match '^\s*$') { return }
    $n, $v = $_ -split '=', 2
    Set-Item -Path "env:$n" -Value $v
}

Write-Host '==> docker compose up (dev overlay, API on 127.0.0.1:8000)'
docker compose -f compose.yaml -f compose.dev.yaml up -d --build

Write-Host '==> integration probe'
docker compose exec -T api python -m app.integration_probe

$alicePw = $env:EAKP_TEST_ALICE_PASSWORD
$bobPw = $env:EAKP_TEST_BOB_PASSWORD
foreach ($pair in @(
    @('alice@test.local', $alicePw),
    @('bob@test.local', $bobPw)
)) {
    $email = $pair[0]
    $pw = $pair[1]
    $pw | docker compose exec -T api python -m app.cli create-user --email $email --password-stdin 2>$null
    if ($LASTEXITCODE -ne 0) { Write-Host "User $email may already exist (ok)" }
}

if (-not (Get-Command python -ErrorAction SilentlyContinue)) {
    throw 'Host Python required for HTTP smoke/eval scripts'
}

Write-Host '==> integration smoke'
python scripts/integration_smoke.py --accept-synthetic-write --url http://127.0.0.1:8000

Write-Host '==> OCR live smoke'
python scripts/ocr_live_smoke.py --accept-synthetic-write --url http://127.0.0.1:8000

Write-Host '==> seed eval corpus + JSONL'
python scripts/seed_synthetic_eval_corpus.py --accept-synthetic-write --url http://127.0.0.1:8000

Write-Host '==> RAG evaluation (Alice)'
$tokenResp = Invoke-RestMethod -Method Post -Uri 'http://127.0.0.1:8000/api/v1/auth/token' `
    -ContentType 'application/json' -Body (@{email='alice@test.local';password=$alicePw} | ConvertTo-Json)
$env:EAKP_EVAL_TOKEN = $tokenResp.access_token
python scripts/evaluate_rag.py --dataset reports/eval_active_alice.jsonl --output reports/rag_eval.json

Write-Host '==> RAG evaluation (Bob ACL)'
$tokenBob = (Invoke-RestMethod -Method Post -Uri 'http://127.0.0.1:8000/api/v1/auth/token' `
    -ContentType 'application/json' -Body (@{email='bob@test.local';password=$bobPw} | ConvertTo-Json)).access_token
$env:EAKP_EVAL_TOKEN = $tokenBob
python scripts/evaluate_rag.py --dataset reports/eval_active_bob.jsonl --output reports/rag_eval_bob_acl.json

Write-Host '==> query load (client-side)'
$env:EAKP_EVAL_TOKEN = $tokenResp.access_token
python scripts/load_test.py --mode query --accept-real-load --seconds 20 --rps 1 `
    --output reports/load_query.json --url http://127.0.0.1:8000

Write-Host '==> preflight'
python scripts/stage8_preflight.py

Write-Host '==> OPEN stubs (explicit NOT_EXECUTED)'
python scripts/open_requirements_register.py

Write-Host 'Done. See reports/ and docs/Stage8_Open_Requirements_UA.md'