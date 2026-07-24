# ParamGuard - One-click start
$root = $PSScriptRoot

Write-Host "============================================" -ForegroundColor Cyan
Write-Host "  ParamGuard - Starting services" -ForegroundColor Cyan
Write-Host "============================================" -ForegroundColor Cyan

# Kill any process on port 8000
$port = netstat -ano | Select-String ":8000.*LISTENING"
if ($port) {
    $pidToKill = ($port -split '\s+')[-1]
    Stop-Process -Id $pidToKill -Force -ErrorAction SilentlyContinue
    Write-Host "[OK] Freed port 8000" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "[1/2] Starting backend..." -ForegroundColor Green
$backendCmd = "title ParamGuard-Backend && cd /d `"$root`" && `"$root\.venv\Scripts\python.exe`" -m uvicorn backend.main:app --host 127.0.0.1 --port 8000 --reload"
Start-Process cmd -ArgumentList "/c $backendCmd"

Write-Host "[2/2] Starting frontend..." -ForegroundColor Green
Start-Process cmd -ArgumentList "/c title ParamGuard-Frontend && cd /d `"$root\frontend`" && npm run dev"

Start-Sleep -Seconds 3

Write-Host ""
Write-Host "  Backend : http://127.0.0.1:8000/docs" -ForegroundColor Cyan
Write-Host "  Frontend: http://localhost:5173" -ForegroundColor Cyan
Write-Host ""
Write-Host "Close the cmd windows to stop services." -ForegroundColor Gray
