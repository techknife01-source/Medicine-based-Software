@echo off
setlocal
cd /d "%~dp0"
echo.
echo  HomoeoCare - frontend-only preview
echo  Opening the static shop in your browser...
echo.
if not exist "%~dp0index.html" (
  echo Could not find index.html. Keep this launcher beside the project files.
  pause
  exit /b 1
)
start "" "%~dp0index.html"
