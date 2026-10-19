@echo off
setlocal EnableDelayedExpansion
title DeepShield - Stop Server

:: =====================================================================
:: DeepShield Windows Safe Shutdown Script
:: Safely stops DeepShield Flask server without killing unrelated Python processes
:: =====================================================================

:: 1. Navigate automatically to the directory containing this batch file
cd /d "%~dp0"

echo =====================================================================
echo             DeepShield Safe Shutdown Utility
echo =====================================================================
echo.
echo [*] Working Directory: %~dp0
echo [*] Searching for active DeepShield process on port 5000...
echo.

set "FOUND=0"

:: 2. Identify process listening on TCP port 5000
for /f "tokens=5" %%a in ('netstat -ano -p tcp ^| findstr /i "LISTENING" ^| findstr /c:":5000 "') do (
    set "TARGET_PID=%%a"
    if defined TARGET_PID (
        for /f "tokens=1 delims=," %%b in ('tasklist /fi "PID eq !TARGET_PID!" /fo csv /nh 2^>nul') do (
            set "PROC_NAME=%%~b"
            echo [INFO] Detected process !PROC_NAME! (PID: !TARGET_PID!) listening on port 5000.
            
            if /i "!PROC_NAME!"=="python.exe" (
                set "FOUND=1"
                echo [INFO] Safely stopping DeepShield server process tree (PID: !TARGET_PID!)...
                taskkill /F /T /PID !TARGET_PID! >nul 2>&1
                if !errorlevel! equ 0 (
                    echo [SUCCESS] DeepShield server process !TARGET_PID! terminated.
                ) else (
                    echo [WARNING] Could not terminate process !TARGET_PID!.
                )
            ) else if /i "!PROC_NAME!"=="pythonw.exe" (
                set "FOUND=1"
                echo [INFO] Safely stopping DeepShield server process tree (PID: !TARGET_PID!)...
                taskkill /F /T /PID !TARGET_PID! >nul 2>&1
                if !errorlevel! equ 0 (
                    echo [SUCCESS] DeepShield server process !TARGET_PID! terminated.
                ) else (
                    echo [WARNING] Could not terminate process !TARGET_PID!.
                )
            ) else (
                echo [WARNING] Process !PROC_NAME! (PID: !TARGET_PID!) is NOT Python.
                echo           Skipping to avoid terminating unrelated system processes.
            )
        )
    )
)

echo.
if !FOUND! equ 0 (
    echo [INFO] No running DeepShield server was detected on port 5000.
) else (
    echo [SUCCESS] DeepShield shutdown completed.
)

echo.
echo Press any key to close this window...
pause >nul
exit /b 0
