@echo off
setlocal

cd /d "%~dp0\.."

net session >nul 2>&1
if %errorlevel% neq 0 (
  powershell -NoProfile -ExecutionPolicy Bypass -Command "Start-Process -FilePath '%~f0' -Verb RunAs"
  exit /b
)

powershell -NoProfile -ExecutionPolicy Bypass -File ".\driver\instalar-impressora-ol1005.ps1"
if %errorlevel% neq 0 (
  echo.
  echo Falha na instalacao da impressora.
  pause
  exit /b 1
)

echo.
echo Instalacao concluida.
pause
exit /b 0
