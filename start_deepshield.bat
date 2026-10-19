@echo off
setlocal EnableDelayedExpansion
title DeepShield - AI Forensics and Synthetic Media Detection

:: =====================================================================
:: DeepShield Windows Startup Script
:: AI-Powered Image Forensics and Synthetic Media Detection Platform
:: =====================================================================

:: 1. Navigate automatically to the directory containing this batch file
cd /d "%~dp0"

echo =====================================================================
echo    DeepShield - AI Forensics and Synthetic Media Detection Platform
echo =====================================================================
echo.
echo [*] Working Directory: %~dp0
echo.

:: 2. Verify backend entry point app.py exists
if not exist "%~dp0app.py" (
    echo [ERROR] Main backend entry point 'app.py' was not found!
    echo         Expected at: "%~dp0app.py"
    echo.
    echo Please make sure this batch file is in the root DeepShield folder.
    echo.
    pause
    exit /b 1
)

:: 3. Check whether virtual environment exists
set "VENV_DIR="
set "ACTIVATE_SCRIPT="

:: Check venv first (if it contains python.exe)
if exist "%~dp0venv\Scripts\activate.bat" (
    if exist "%~dp0venv\Scripts\python.exe" (
        set "VENV_DIR=%~dp0venv"
        set "ACTIVATE_SCRIPT=%~dp0venv\Scripts\activate.bat"
        goto :VenvResolved
    )
)

:: Fall back to .venv if venv is missing python.exe
if exist "%~dp0.venv\Scripts\activate.bat" (
    if exist "%~dp0.venv\Scripts\python.exe" (
        echo [INFO] Detected complete virtual environment in '.venv'.
        set "VENV_DIR=%~dp0.venv"
        set "ACTIVATE_SCRIPT=%~dp0.venv\Scripts\activate.bat"
        goto :VenvResolved
    )
)

:: Error handling if no working virtual environment is found
if exist "%~dp0venv\Scripts\activate.bat" (
    echo [ERROR] Virtual environment 'venv' was found, but 'venv\Scripts\python.exe' is missing!
    echo         Please ensure Python is properly installed inside your virtual environment.
    echo.
    pause
    exit /b 1
)

echo [ERROR] Virtual environment folder not found!
echo         Expected 'venv' or '.venv' with 'Scripts\activate.bat'.
echo         Looked in: "%~dp0"
echo.
echo Please ensure the virtual environment exists before launching DeepShield.
echo.
pause
exit /b 1

:VenvResolved
echo [*] Activating virtual environment: "!VENV_DIR!"
call "!ACTIVATE_SCRIPT!"
if !errorlevel! neq 0 (
    echo [ERROR] Failed to activate virtual environment at "!ACTIVATE_SCRIPT!".
    echo.
    pause
    exit /b 1
)

:: Verify python command is available in active environment
where python >nul 2>&1
if !errorlevel! neq 0 (
    echo [ERROR] 'python' command is unavailable after activating virtual environment.
    echo.
    pause
    exit /b 1
)

echo [*] Python environment ready:
python -c "import sys; print('    ' + sys.executable + ' (Python ' + sys.version.split()[0] + ')')"
echo.

:: 4. Check whether port 5000 is already in use
netstat -ano -p tcp | findstr /i "LISTENING" | findstr /c:":5000 " >nul 2>&1
if !errorlevel! equ 0 (
    echo [WARNING] Port 5000 is already in use by another process!
    echo           If an older DeepShield instance is running, run 'stop_deepshield.bat' first.
    echo.
)

:: 5. Launch background browser opener (polls port 5000 until Flask accepts connections)
echo [*] DeepShield UI will automatically open at: http://127.0.0.1:5000
echo [*] Waiting for Flask server initialization...
echo.
start "" powershell -WindowStyle Hidden -NoProfile -ExecutionPolicy Bypass -Command "$attempts = 0; while ($attempts -lt 60) { Start-Sleep -Seconds 1; try { $tcp = New-Object System.Net.Sockets.TcpClient('127.0.0.1', 5000); $tcp.Close(); Start-Sleep -Milliseconds 500; Start-Process 'http://127.0.0.1:5000'; break; } catch { $attempts++; } }"

:: 6. Run Flask application in foreground to keep logs and tracebacks visible
echo =====================================================================
echo    Starting DeepShield Server (Press Ctrl+C in this window to stop)
echo    Loading PyTorch and Transformers AI models into memory...
echo =====================================================================
echo.

python "%~dp0app.py"

:: 7. Keep window open on exit/error so user can view logs
set "EXIT_CODE=%errorlevel%"
echo.
echo =====================================================================
if %EXIT_CODE% neq 0 (
    echo [ERROR] DeepShield server stopped unexpectedly with exit code: %EXIT_CODE%
) else (
    echo [INFO] DeepShield server has stopped.
)
echo =====================================================================
echo.
echo Press any key to close this terminal...
pause >nul
