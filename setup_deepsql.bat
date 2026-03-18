@echo off
setlocal

powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0setup_deepsql.ps1" %*
if errorlevel 1 (
  echo.
  echo Error en setup_deepsql.ps1
  exit /b 1
)

endlocal
