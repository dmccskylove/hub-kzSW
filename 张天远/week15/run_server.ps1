# Run server (PowerShell)
# Usage: $env:DEEPSEEK_API_KEY="sk-xxx"; .\run_server.ps1

param([int]$Port = 8000)

if (-not $env:DEEPSEEK_API_KEY) {
    Write-Host "[ERROR] DEEPSEEK_API_KEY not set!" -ForegroundColor Red
    Write-Host "  Run first: `$env:DEEPSEEK_API_KEY = 'sk-xxx'"
    exit 1
}

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $scriptDir

Write-Host "[INFO] Project dir: $scriptDir"
Write-Host "[INFO] Port: $Port"
Write-Host "[INFO] API docs: http://localhost:$Port/docs"
Write-Host ""

uvicorn src.server:app --host 0.0.0.0 --port $Port --reload
