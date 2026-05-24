@echo off
setlocal

net session >nul 2>&1
if %errorlevel% neq 0 (
  powershell -NoProfile -ExecutionPolicy Bypass -Command "Start-Process -FilePath '%~f0' -Verb RunAs"
  exit /b
)

if exist "%~dp0instalar-impressora-ol1005.ps1" (
  powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0instalar-impressora-ol1005.ps1"
) else (
  echo Nao encontrei instalar-impressora-ol1005.ps1 na mesma pasta.
  echo Baixe tambem o arquivo .ps1 padrao no assistente.
  pause
  exit /b 1
)

if %errorlevel% neq 0 (
  echo Falha na instalacao da impressora.
  pause
  exit /b 1
)

echo.
echo Instalacao concluida.
pause
exit /b 0
