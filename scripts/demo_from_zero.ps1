#Requires -Version 5.1
# Відтворюване синтетичне демо EAKP (Windows). Лише throwaway-стенд.
$ErrorActionPreference = 'Stop'
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root

function Assert-LastExitCode {
    param(
        [string]$Step,
        [int[]]$Allow = @()
    )
    if ($Allow -contains $LASTEXITCODE) { return }
    if ($LASTEXITCODE -ne 0) {
        throw "Step failed: $Step (exit code $LASTEXITCODE)"
    }
}

function Invoke-External {
    param(
        [string]$Step,
        [string]$FilePath,
        [string[]]$ArgumentList = @(),
        [int[]]$AllowExit = @()
    )
    Write-Host "==> $Step"
    & $FilePath @ArgumentList
    Assert-LastExitCode -Step $Step -Allow $AllowExit
}

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
Assert-LastExitCode 'docker compose up'

Write-Host '==> integration probe'
docker compose exec -T api python -m app.integration_probe
Assert-LastExitCode 'integration_probe'

$alicePw = $env:EAKP_TEST_ALICE_PASSWORD
$bobPw = $env:EAKP_TEST_BOB_PASSWORD
foreach ($pair in @(
    @('alice@test.local', $alicePw),
    @('bob@test.local', $bobPw)
)) {
    $email = $pair[0]
    $pw = $pair[1]
    Write-Host "==> create-user $email"
    $createOut = ($pw | docker compose exec -T api python -m app.cli create-user --email $email --password-stdin 2>&1)
    if ($LASTEXITCODE -ne 0 -and ($createOut -join ' ') -notmatch 'already exists') {
        throw "Step failed: create-user $email (exit $LASTEXITCODE)"
    }
}

if (-not (Get-Command python -ErrorAction SilentlyContinue)) {
    throw 'Host Python required for HTTP smoke/eval scripts'
}

Invoke-External 'integration smoke' 'python' @(
    'scripts/integration_smoke.py', '--accept-synthetic-write', '--url', 'http://127.0.0.1:8000'
)
Invoke-External 'OCR live smoke' 'python' @(
    'scripts/ocr_live_smoke.py', '--accept-synthetic-write', '--url', 'http://127.0.0.1:8000'
)
Invoke-External 'seed eval corpus' 'python' @(
    'scripts/seed_synthetic_eval_corpus.py', '--accept-synthetic-write', '--url', 'http://127.0.0.1:8000'
)

Write-Host '==> RAG evaluation (Alice)'
$tokenResp = Invoke-RestMethod -Method Post -Uri 'http://127.0.0.1:8000/api/v1/auth/token' `
    -ContentType 'application/json' -Body (@{email='alice@test.local';password=$alicePw} | ConvertTo-Json)
$env:EAKP_EVAL_TOKEN = $tokenResp.access_token
Invoke-External 'evaluate_rag Alice' 'python' @(
    'scripts/evaluate_rag.py', '--dataset', 'reports/eval_active_alice.jsonl', '--output', 'reports/rag_eval.json'
)

Write-Host '==> RAG evaluation (Bob ACL)'
$tokenBob = (Invoke-RestMethod -Method Post -Uri 'http://127.0.0.1:8000/api/v1/auth/token' `
    -ContentType 'application/json' -Body (@{email='bob@test.local';password=$bobPw} | ConvertTo-Json)).access_token
$env:EAKP_EVAL_TOKEN = $tokenBob
Invoke-External 'evaluate_rag Bob' 'python' @(
    'scripts/evaluate_rag.py', '--dataset', 'reports/eval_active_bob.jsonl', '--output', 'reports/rag_eval_bob_acl.json'
)

Write-Host '==> query load (client-side)'
$env:EAKP_EVAL_TOKEN = $tokenResp.access_token
Invoke-External 'load_test query' 'python' @(
    'scripts/load_test.py', '--mode', 'query', '--accept-real-load', '--seconds', '20', '--rps', '1',
    '--output', 'reports/load_query.json', '--url', 'http://127.0.0.1:8000'
)

Invoke-External 'stage8 preflight' 'python' @('scripts/stage8_preflight.py')
Invoke-External 'open requirements register' 'python' @('scripts/open_requirements_register.py')

Write-Host 'Done. See reports/ and docs/Stage8_Open_Requirements_UA.md'