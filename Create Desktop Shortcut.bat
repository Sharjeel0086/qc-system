@echo off
rem Creates a "Quality Cross-Check System" shortcut on the desktop, pointing
rem at the silent launcher. Run this once; delete it afterwards if you like.
cd /d "%~dp0"

set TARGET=%cd%\Run QC System (no console window).bat
set SHORTCUT=%USERPROFILE%\Desktop\Quality Cross-Check System.lnk

powershell -NoProfile -Command ^
  "$s = (New-Object -COM WScript.Shell).CreateShortcut('%SHORTCUT%');" ^
  "$s.TargetPath = '%TARGET%';" ^
  "$s.WorkingDirectory = '%cd%';" ^
  "$s.IconLocation = 'shell32.dll,167';" ^
  "$s.Description = 'Quality Cross-Check System';" ^
  "$s.Save()"

if exist "%SHORTCUT%" (
    echo Shortcut created on the desktop.
) else (
    echo Could not create the shortcut. You can still run the program
    echo by double-clicking "Run QC System.bat" in this folder.
)
pause
