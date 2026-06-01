@echo off
REM job-hunt CLI wrapper for Windows
REM 直接调用 job_hunt.cli 入口

setlocal
set "SCRIPT_DIR=%~dp0"
set "PROJECT_ROOT=%SCRIPT_DIR%.."
set "PYTHONPATH=%PROJECT_ROOT%\src;%PYTHONPATH%"

REM 强制 UTF-8 编码，解决 Windows GBK 终端 emoji 乱码问题
set PYTHONIOENCODING=utf-8
set PYTHONUTF8=1
chcp 65001 >nul 2>&1

python -m job_hunt.cli %*
endlocal
