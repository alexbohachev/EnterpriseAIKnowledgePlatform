# Zip Stage 8 live evidence for OTUS (no .env, .secrets, or DB dumps).
$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
$stamp = Get-Date -Format 'yyyy-MM-dd'
$zip = Join-Path $root "reports\EAKP_Stage8_Live_Evidence_$stamp.zip"
$staging = Join-Path $env:TEMP "eakp_stage8_bundle_$stamp"
if (Test-Path $staging) { Remove-Item $staging -Recurse -Force }
New-Item -ItemType Directory -Path $staging | Out-Null

$commit = (git -C $root rev-parse HEAD 2>$null)
if (-not $commit) { $commit = 'unknown' }
$manifest = @{
  generated_utc = (Get-Date).ToUniversalTime().ToString('o')
  git_commit = $commit
  repository = 'https://github.com/alexbohachev/EnterpriseAIKnowledgePlatform'
  bundle_script = 'scripts/bundle_stage8_evidence.ps1'
  note = 'Synthetic Docker evidence; re-run scripts/demo_from_zero.ps1 to refresh JSON.'
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
  'presentation\EAKP_OTUS_Defense_Stage8_UA.pdf',
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
Write-Host "Created: $zip"