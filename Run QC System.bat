@echo off
setlocal enabledelayedexpansion
title Quality Cross-Check System
cd /d "%~dp0"

rem --- find a working Python -------------------------------------------
set PYEXE=

where py >nul 2>nul
if not errorlevel 1 (
    py -3 --version >nul 2>nul
    if not errorlevel 1 set PYEXE=py -3
)

if "%PYEXE%"=="" (
    where python >nul 2>nul
    if not errorlevel 1 (
        python --version >nul 2>nul
        if not errorlevel 1 set PYEXE=python
    )
)

if "%PYEXE%"=="" (
    echo.
    echo  ============================================================
    echo   Python was not found on this computer.
    echo.
    echo   Install Python from https://www.python.org/downloads/
    echo   During setup, tick "Add python.exe to PATH", and make sure
    echo   "tcl/tk and IDLE" is included ^(it is ticked by default^).
    echo  ============================================================
    echo.
    pause
    exit /b 1
)

rem --- make sure tkinter is available ------------------------------------
%PYEXE% -c "import tkinter" >nul 2>nul
if errorlevel 1 (
    echo.
    echo  ============================================================
    echo   Python was found, but the tkinter module is missing.
    echo.
    echo   Re-run the Python installer, choose "Modify", and tick
    echo   "tcl/tk and IDLE".
    echo  ============================================================
    echo.
    pause
    exit /b 1
)

rem --- run the app ---------------------------------------------------------
%PYEXE% app.py
if errorlevel 1 (
    echo.
    echo  ============================================================
    echo   The program closed with an error ^(see above^).
    echo  ============================================================
    echo.
    pause
)

endlocal
