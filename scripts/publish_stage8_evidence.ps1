#Requires -Version 5.1
# Після успішного demo_from_zero: verify → bundle → upload GitHub Release.
param(
    [string]$ReleaseTag = 'stage8-submission-2026-11-17'
)
$ErrorActionPreference = 'Stop'
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root

$head = (git rev-parse HEAD).Trim()
Write-Host "Git HEAD: $head"

if (Get-Command py -ErrorAction SilentlyContinue) {
    py -3 scripts/verify_mvp_evidence.py
} else {
    python scripts/verify_mvp_evidence.py
}
if ($LASTEXITCODE -ne 0) { throw "verify_mvp_evidence failed (exit $LASTEXITCODE)" }

powershell -ExecutionPolicy Bypass -File scripts\bundle_stage8_evidence.ps1
$zip = Get-ChildItem reports\EAKP_Stage8_Live_Evidence_*.zip | Sort-Object LastWriteTime -Descending | Select-Object -First 1
if (-not $zip) { throw 'No evidence ZIP found' }

gh release upload $ReleaseTag $zip.FullName --clobber
gh release upload $ReleaseTag presentation\EAKP_OTUS_Defense_Stage8_UA.pptx --clobber
Write-Host "Uploaded $($zip.Name) for commit $head to release $ReleaseTag"