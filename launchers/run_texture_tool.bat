@echo off
setlocal

set SCRIPT_DIR=%~dp0
set PROJECT_ROOT=%SCRIPT_DIR%..
python "%PROJECT_ROOT%\texture_resize_tool.py" %*

if errorlevel 1 (
    echo.
    echo Processing failed.
    pause
)
