# Zip Stage 8 live evidence for OTUS (no .env, .secrets, or DB dumps).
$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
$stamp = Get-Date -Format 'yyyy-MM-dd'
$zip = Join-Path $root "reports\EAKP_Stage8_Live_Evidence_$stamp.zip"
$staging = Join-Path $env:TEMP "eakp_stage8_bundle_$stamp"
if (Test-Path $staging) { Remove-Item $staging -Recurse -Force }
New-Item -ItemType Directory -Path $staging | Out-Null

$paths = @(
  'reports\stage8_live_evidence_manifest.json',
  'reports\stage8_preflight.json',
  'reports\integration_smoke.json',
  'reports\ocr_live_e2e.json',
  'reports\load_health.json',
  'reports\load_query.json',
  'reports\rag_eval.json',
  'reports\rag_eval_bob_acl.json',
  'reports\screenshots',
  'examples\eval_live_synthetic.jsonl',
  'examples\eval_live_bob_acl.jsonl',
  'docs\Stage8_OTUS_Demo_Script_UA.md',
  'docs\Stage8_Acceptance_Gap_Analysis_UA.md'
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
Write-Host "Created: $zip"