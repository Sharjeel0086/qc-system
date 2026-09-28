@echo off
rem This version hides the black command window. Use "Run QC System.bat"
rem instead if you need to see an error message - this one writes errors
rem to error_log.txt but shows nothing on screen.
cd /d "%~dp0"

set PYW=

where pyw >nul 2>nul
if not errorlevel 1 set PYW=pyw -3

if "%PYW%"=="" (
    where pythonw >nul 2>nul
    if not errorlevel 1 set PYW=pythonw
)

if "%PYW%"=="" (
    rem Fall back to the console version so the person can see what's wrong.
    call "Run QC System.bat"
    exit /b
)

start "" %PYW% app.py 2> error_log.txt
