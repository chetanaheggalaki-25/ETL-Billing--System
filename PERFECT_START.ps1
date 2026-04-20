# ============================================================
# PERFECT_START.ps1 - Merged ETL Billing System
# ============================================================

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "   IntelliExtract - Perfect Merge       " -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan

$backendDir = "c:\Users\Chetana\Downloads\dummy\etl-app\backend"
$frontendDir = "c:\Users\Chetana\Downloads\dummy\chetana\UI WORKING"

# 1. Start FastAPI Backend (Port 5000)
Write-Host "[1/3] Starting FastAPI Engine (Port 5000)..." -ForegroundColor Yellow
Start-Process powershell -ArgumentList @(
    "-NoExit",
    "-Command",
    "cd '$backendDir'; uvicorn main:app --reload --port 5000"
) -WindowStyle Normal

# 2. Start Node Auth Server (Port 3001)
Write-Host "[2/3] Starting Auth Server (Port 3001)..." -ForegroundColor Yellow
Start-Process powershell -ArgumentList @(
    "-NoExit",
    "-Command",
    "cd '$frontendDir'; node server.js"
) -WindowStyle Normal

# 3. Start Premium UI (Port 5173)
Write-Host "[3/3] Starting Premium Dashboard..." -ForegroundColor Yellow
Start-Process powershell -ArgumentList @(
    "-NoExit",
    "-Command",
    "cd '$frontendDir'; npm run dev"
) -WindowStyle Normal

Start-Sleep -Seconds 5

# 4. Open Browser
Write-Host "Opening http://localhost:5173 ..." -ForegroundColor Green
Start-Process "http://localhost:5173"

Write-Host "Merge Complete! System is LIVE." -ForegroundColor Green
