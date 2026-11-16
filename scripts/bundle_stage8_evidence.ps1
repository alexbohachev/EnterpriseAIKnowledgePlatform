# Zip Stage 8 live evidence for OTUS (no .env, .secrets, or DB dumps).
param(
    [switch]$AllowStaleEvidence
)
$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
Set-Location $root

if (-not $AllowStaleEvidence) {
    Write-Host '==> verify MVP evidence (reports must match current code gates)'
    python scripts/verify_mvp_evidence.py
    if ($LASTEXITCODE -ne 0) {
        throw @"
MVP evidence verification failed (exit $LASTEXITCODE).
Run: powershell -File scripts\demo_from_zero.ps1
Then re-run this bundle script, or pass -AllowStaleEvidence only for inspection.
"@
    }
}

$stamp = Get-Date -Format 'yyyy-MM-dd'
$zip = Join-Path $root "reports\EAKP_Stage8_Live_Evidence_$stamp.zip"
$staging = Join-Path $env:TEMP "eakp_stage8_bundle_$stamp"
if (Test-Path $staging) { Remove-Item $staging -Recurse -Force }
New-Item -ItemType Directory -Path $staging | Out-Null

$commit = (git -C $root rev-parse HEAD 2>$null)
if (-not $commit) { $commit = 'unknown' }
$preflightCommit = $null
$preflightPath = Join-Path $root 'reports\stage8_preflight.json'
if (Test-Path $preflightPath) {
    $preflightCommit = (Get-Content $preflightPath -Raw | ConvertFrom-Json).git_commit
}
$manifest = @{
  evidence_bundle_schema_version = 1
  generated_utc = (Get-Date).ToUniversalTime().ToString('o')
  git_commit = $commit
  preflight_git_commit = $preflightCommit
  repository = 'https://github.com/alexbohachev/EnterpriseAIKnowledgePlatform'
  bundle_script = 'scripts/bundle_stage8_evidence.ps1'
  note = 'Bundle only after demo_from_zero + mvp_acceptance PASS; upload to GitHub Release with matching tag.'
  open_requirements = 'docs/Stage8_Open_Requirements_UA.md'
} | ConvertTo-Json -Depth 4
$manifestPath = Join-Path $root 'reports\stage8_live_evidence_manifest.json'
New-Item -ItemType Directory -Force (Split-Path $manifestPath) | Out-Null
Set-Content -Path $manifestPath -Value $manifest -Encoding utf8

$paths = @(
  'reports\stage8_live_evidence_manifest.json',
  'reports\stage8_preflight.json',
  'reports\integration_smoke.json',
  'reports\ocr_live_e2e.json',
  'reports\load_health.json',
  'reports\load_query.json',
  'reports\rag_eval.json',
  'reports\rag_eval_bob_acl.json',
  'reports\open_requirements_register.json',
  'reports\eval_seed_manifest.json',
  'reports\eval_active_alice.jsonl',
  'reports\eval_active_bob.jsonl',
  'reports\screenshots',
  'examples\eval_live_synthetic.jsonl',
  'examples\eval_live_bob_acl.jsonl',
  'examples\EVAL_DATASETS_UA.md',
  'docs\Stage8_Evidence_Rebuild_UA.md',
  'docs\Stage8_OTUS_Demo_Script_UA.md',
  'docs\Stage8_Acceptance_Gap_Analysis_UA.md',
  'docs\Stage8_Submission_Checklist_UA.md',
  'docs\Stage8_Open_Requirements_UA.md',
  'docs\Stage8_Defense_Speech_Addendum_UA.md',
  'scripts\demo_from_zero.ps1',
  'scripts\demo_from_zero.sh',
  'scripts\demo_env.example',
  'presentation\EAKP_OTUS_Defense_UA.pdf',
  'presentation\EAKP_OTUS_Defense_Stage8_UA.pptx',
  'docs\Stage8_Demo_Rehearsal_Checklist_UA.md',
  'docs\Stage8_Demo_Teleprompter_UA.md',
  'docs\Stage8_OTUS_Submission_Cover_Letter_UA.md'
)
foreach ($rel in $paths) {
  $src = Join-Path $root $rel
  if (-not (Test-Path $src)) { Write-Warning "Skip missing: $rel"; continue }
  $dest = Join-Path $staging $rel
  New-Item -ItemType Directory -Force (Split-Path $dest) | Out-Null
  Copy-Item $src $dest -Recurse -Force
}
if (Test-Path $zip) { Remove-Item $zip -Force }
Compress-Archive -Path (Join-Path $staging '*') -DestinationPath $zip -CompressionLevel Optimal
Remove-Item $staging -Recurse -Force
Write-Host "Created: $zip (git $commit)"