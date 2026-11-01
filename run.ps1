# NewsEdge PowerShell One-Click Runner
$ErrorActionPreference = "Continue"
Set-Location $PSScriptRoot

Write-Host "=====================================================================" -ForegroundColor Cyan
Write-Host "Starting NewsEdge Automated Pipeline..." -ForegroundColor Cyan
Write-Host "=====================================================================" -ForegroundColor Cyan

if (Test-Path ".venv\Scripts\python.exe") {
    & .venv\Scripts\python.exe run_newsedge.py @args
} else {
    & python run_newsedge.py @args
}

if ($LASTEXITCODE -ne 0) {
    Write-Host "`n[ERROR] Pipeline completed with exit code $LASTEXITCODE. Check logs/newsedge.log for details." -ForegroundColor Red
}

Write-Host "`nPress any key to exit..." -ForegroundColor Gray
if ([Environment]::UserInteractive -and -not $Host.Name.Contains("ServerRemoteHost")) {
    $null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")
}
