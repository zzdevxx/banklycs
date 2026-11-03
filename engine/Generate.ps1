# ==============================================================================
# PROPRESENTER 7 MASTER BANKS GENERATOR (THEME ZZ)
# Letak: .\Generate.ps1 (root workspace)
# ==============================================================================
param (
    [string]$BaseDir = $PSScriptRoot,
    [switch]$RebuildEngine,
    [switch]$Full
)

$ErrorActionPreference = "Stop"

Write-Host "==============================================================================" -ForegroundColor Cyan
Write-Host "  PROPRESENTER 7 - MASTER BANKS GENERATOR & CLEANUP" -ForegroundColor Cyan
Write-Host "==============================================================================" -ForegroundColor Cyan

$engineDir   = $PSScriptRoot
$engineExe   = Join-Path $engineDir "banklycs.exe"
$projectFile = Join-Path $engineDir "ProEngine.csproj"

if ($RebuildEngine -or (-not (Test-Path $engineExe))) {
    Write-Host "`n[BUILD] Mengompilasi engine C# ProEngine..." -ForegroundColor Yellow
    if (-not (Test-Path $projectFile)) {
        throw "File project ProEngine tidak ditemukan di: $projectFile"
    }
    dotnet publish $projectFile -c Release -o $engineDir | Out-Null
    Write-Host "  -> Engine berhasil dibangun di: $engineExe" -ForegroundColor Green
}

if ($Full) {
    Write-Host "  [MODE] FULL REBUILD (library & playlist akan dibersihkan)" -ForegroundColor Yellow
    & $engineExe $BaseDir --full
} else {
    Write-Host "  [MODE] Incremental (playlist ibadah & library lain aman)" -ForegroundColor Green
    & $engineExe $BaseDir
}
if ($LASTEXITCODE -ne 0) {
    Write-Host "`n[WARNING] Pipeline selesai dengan error (exit $LASTEXITCODE). Cek Engine\last_errors.txt" -ForegroundColor Red
    exit $LASTEXITCODE
}

Write-Host "`n[SELESAI] Pipeline Master Banks selesai dijalankan." -ForegroundColor Green
