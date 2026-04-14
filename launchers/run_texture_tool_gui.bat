@echo off
setlocal

set SCRIPT_DIR=%~dp0
set PROJECT_ROOT=%SCRIPT_DIR%..
python "%PROJECT_ROOT%\texture_resize_gui.py"

if errorlevel 1 (
    echo.
    echo GUI failed to start.
    pause
)
