@echo off
echo Installing AuraSafe auto-startup...
set TASK_NAME=AuraSafe
set SCRIPT_DIR=%~dp0..
schtasks /Create /TN "%TASK_NAME%" /XML "%~dp0aurasafe_windows_startup.xml" /F
if %errorlevel% == 0 (
    echo [OK] AuraSafe will now start automatically on login.
) else (
    echo [ERROR] Failed to register task. Try running as Administrator.
)
pause
