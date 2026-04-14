@echo off
setlocal

set SCRIPT_DIR=%~dp0
call "%SCRIPT_DIR%launchers\run_texture_tool_gui.bat"

if errorlevel 1 (
    echo.
    echo GUI failed to start.
    pause
)
