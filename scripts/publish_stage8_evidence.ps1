#Requires -Version 5.1
# Після успішного demo_from_zero: verify → bundle → upload GitHub Release.
param(
    [string]$ReleaseTag = 'stage8-submission-2026-11-17'
)
$ErrorActionPreference = 'Stop'
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root

function Assert-ExitCode {
    param([string]$Step, [int]$Code = $LASTEXITCODE)
    if ($Code -ne 0) {
        throw "Step failed: $Step (exit code $Code)"
    }
}

function Invoke-Gh {
    param([string]$Step, [string[]]$ArgumentList)
    $prev = $ErrorActionPreference
    $ErrorActionPreference = 'Continue'
    Write-Host "==> $Step"
    & gh @ArgumentList
    $code = $LASTEXITCODE
    $ErrorActionPreference = $prev
    Assert-ExitCode -Step $Step -Code $code
}

$head = (git rev-parse HEAD).Trim()
Write-Host "Git HEAD: $head"

Write-Host '==> verify MVP evidence'
if (Get-Command py -ErrorAction SilentlyContinue) {
    py -3 scripts/verify_mvp_evidence.py
} else {
    python scripts/verify_mvp_evidence.py
}
Assert-ExitCode 'verify_mvp_evidence'

$bundleStarted = Get-Date
Write-Host '==> bundle evidence ZIP'
$prev = $ErrorActionPreference
$ErrorActionPreference = 'Continue'
& powershell -ExecutionPolicy Bypass -File (Join-Path $Root 'scripts\bundle_stage8_evidence.ps1')
$bundleCode = $LASTEXITCODE
$ErrorActionPreference = $prev
Assert-ExitCode 'bundle_stage8_evidence' -Code $bundleCode

$marker = Join-Path $Root 'reports\last_evidence_bundle.txt'
if (-not (Test-Path $marker)) {
    throw 'Bundle marker missing: reports/last_evidence_bundle.txt'
}
$zipPath = (Get-Content $marker -Raw).Trim()
if (-not (Test-Path -LiteralPath $zipPath)) {
    throw "Bundle path from marker does not exist: $zipPath"
}
$zipInfo = Get-Item -LiteralPath $zipPath
if ($zipInfo.LastWriteTime -lt $bundleStarted.AddSeconds(-5)) {
    throw "ZIP is older than this bundle run (stale artifact?): $zipPath"
}

$pptx = Join-Path $Root 'presentation\EAKP_OTUS_Defense_Stage8_UA.pptx'
if (-not (Test-Path $pptx)) {
    throw "Presentation not found: $pptx"
}

Invoke-Gh 'gh release upload ZIP' @('release', 'upload', $ReleaseTag, $zipPath, '--clobber')
Invoke-Gh 'gh release upload PPTX' @('release', 'upload', $ReleaseTag, $pptx, '--clobber')

Write-Host "Uploaded $($zipInfo.Name) and PPTX for commit $head to release $ReleaseTag"
Write-Host "Verify manifest git_commit inside ZIP matches: $head"