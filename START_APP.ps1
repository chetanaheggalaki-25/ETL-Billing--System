# ============================================================
#  START_APP.ps1  —  Unified Startup Script
#  Shreyash (Python Flask ETL Backend)  +  Chetana (React UI)
# ============================================================

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "   IntelliBill Extract - Full Stack     " -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# --- Paths ---
$backendDir  = "$PSScriptRoot\shreyash\ETL_GRP (1)\ETL_GRP\ETL_2"
$frontendDir = "$PSScriptRoot\chetana\UI WORKING"

# --- 1. Start Python Flask ETL Backend (Port 5000) ---
Write-Host "[1/3] Starting Python Flask ETL Backend (port 5000)..." -ForegroundColor Yellow
Start-Process powershell -ArgumentList @(
    "-NoExit",
    "-Command",
    "cd '$backendDir'; Write-Host 'Flask ETL Backend starting...' -ForegroundColor Green; python app.py"
) -WindowStyle Normal

Start-Sleep -Seconds 3

# --- 2. Start Node.js Auth Server (Port 3001) ---
Write-Host "[2/3] Starting Node.js Auth Server (port 3001)..." -ForegroundColor Yellow
Start-Process powershell -ArgumentList @(
    "-NoExit",
    "-Command",
    "cd '$frontendDir'; Write-Host 'Node Auth Server starting...' -ForegroundColor Green; node server.js"
) -WindowStyle Normal

Start-Sleep -Seconds 2

# --- 3. Start React Vite Dev Server (Port 5173) ---
Write-Host "[3/3] Starting React Vite Dev Server (port 5173)..." -ForegroundColor Yellow
Start-Process powershell -ArgumentList @(
    "-NoExit",
    "-Command",
    "cd '$frontendDir'; Write-Host 'React Frontend starting...' -ForegroundColor Green; npm run dev"
) -WindowStyle Normal

Start-Sleep -Seconds 4

# --- 4. Open Browser ---
Write-Host ""
Write-Host "Opening browser at http://localhost:5173 ..." -ForegroundColor Green
Start-Process "http://localhost:5173"

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  All servers started successfully!     " -ForegroundColor Green
Write-Host "                                        "
Write-Host "  Flask  ETL Backend : http://localhost:5000" -ForegroundColor White
Write-Host "  Node   Auth Server : http://localhost:3001" -ForegroundColor White
Write-Host "  React  Frontend    : http://localhost:5173" -ForegroundColor White
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Close the individual terminal windows to stop each server." -ForegroundColor Gray
