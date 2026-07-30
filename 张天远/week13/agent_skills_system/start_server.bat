@echo off
REM ============================================
REM   Agent Skills System — 启动后端服务
REM   使用方式: 先设置 DEEPSEEK_API_KEY 环境变量
REM     set DEEPSEEK_API_KEY=sk-xxx
REM     start_server.bat
REM ============================================

if "%DEEPSEEK_API_KEY%"=="" (
    echo [ERROR] DEEPSEEK_API_KEY 未设置！
    echo 请先执行: set DEEPSEEK_API_KEY=sk-xxx
    pause
    exit /b 1
)

cd /d "%~dp0"
echo [INFO] 项目目录: %cd%
echo [INFO] 启动端口: 8000
echo [INFO] API docs: http://localhost:8000/docs
echo.

uvicorn src.server:app --host 0.0.0.0 --port 8000
