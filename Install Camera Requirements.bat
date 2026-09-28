@echo off
rem Installs the packages the camera features need.  Code 39 decoding is
rem built into camera.py, so this project does NOT require ZBar/pyzbar or
rem administrator-installed Windows DLLs for alphanumeric serial labels.
cd /d "%~dp0"
title Install camera requirements

set PYEXE=
where py >nul 2>nul
if not errorlevel 1 set PYEXE=py -3
if "%PYEXE%"=="" (
    where python >nul 2>nul
    if not errorlevel 1 set PYEXE=python
)
if "%PYEXE%"=="" (
    echo Python was not found.
    pause
    exit /b 1
)

echo Removing conflicting OpenCV installations first...
rem Having opencv-python and opencv-contrib-python installed together can
rem cause import conflicts.  This step only affects Python packages and does
rem not require administrator rights when Python is installed per-user.
%PYEXE% -m pip uninstall -y opencv-python opencv-python-headless opencv-contrib-python-headless >nul 2>nul

echo.
echo Installing OpenCV-contrib, Pillow and OCR wrapper...
%PYEXE% -m pip install --upgrade pip
%PYEXE% -m pip install -r requirements.txt

echo.
echo ============================================================
echo  CODE 39 BARCODE DECODING:
echo  Built into this application - no pyzbar, ZBar DLL or admin
 echo  installation is required for Code 39 serial-number labels.
echo.
echo  OCR (optional): pip installs the pytesseract wrapper only.
echo  The separate Tesseract program is only needed if you want
 echo  OCR cross-checking of the printed serial number.
echo ============================================================
echo.

echo Checking what actually loaded...
%PYEXE% -c "import camera; camera.print_diagnostics()"

echo.
echo Done. Close this window and start the program.
pause
