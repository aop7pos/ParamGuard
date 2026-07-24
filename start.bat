@echo off
echo ============================================
echo   ParamGuard - 启动前后端
echo ============================================

echo [1/2] 启动 Python 后端 (FastAPI)...
start "ParamGuard-Backend" cmd /c "cd /d %~dp0 && .venv\Scripts\python.exe -m uvicorn backend.main:app --host 127.0.0.1 --port 8000 --reload"

echo [2/2] 启动前端 (Vite)...
start "ParamGuard-Frontend" cmd /c "cd /d %~dp0frontend && npm run dev"

echo.
echo 后端: http://127.0.0.1:8000/docs
echo 前端: http://localhost:5173
echo.
echo 关闭窗口即可停止服务。
pause
