# Run CLI client (PowerShell)
# Usage: .\run_cli.ps1 [-Port 8080]

param([int]$Port = 8000)

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $scriptDir

python -m src.cli --port $Port
