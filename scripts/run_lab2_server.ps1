Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

Set-Location -Path (Split-Path -Parent $PSScriptRoot)
$env:APP_USE_MOCK_DB = "true"
$env:APP_SEED_DEMO = "true"

& ".\.venv\Scripts\python.exe" -m uvicorn app.main:app --host 127.0.0.1 --port 10104
