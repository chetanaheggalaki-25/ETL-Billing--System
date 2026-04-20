# ============================================================
# RUN_ETL_APP.ps1 - Unified ETL Billing App Launcher
# ============================================================

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "   Starting ETL Billing System...       " -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan

$backendDir = "$PSScriptRoot\backend"
$frontendDir = "$PSScriptRoot\frontend"

# 1. Start FastAPI Backend (Port 8000)
Write-Host "[1/2] Starting Backend (Port 8000)..." -ForegroundColor Yellow
Start-Process powershell -ArgumentList @(
    "-NoExit",
    "-Command",
    "cd '$backendDir'; uvicorn main:app --reload --port 8000"
) -WindowStyle Normal

# 2. Start React Vite Frontend (Port 5173)
Write-Host "[2/2] Starting Frontend (Port 5173)..." -ForegroundColor Yellow
Start-Process powershell -ArgumentList @(
    "-NoExit",
    "-Command",
    "cd '$frontendDir'; npm run dev"
) -WindowStyle Normal

Start-Sleep -Seconds 5

# 3. Open Browser
Write-Host "Opening http://localhost:5173 ..." -ForegroundColor Green
Start-Process "http://localhost:5173"

Write-Host "Setup Complete!" -ForegroundColor Green
