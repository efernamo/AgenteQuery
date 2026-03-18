@echo off
setlocal

powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0uninstall_deepsql.ps1" %*
if errorlevel 1 (
  echo.
  echo Error en uninstall_deepsql.ps1
  exit /b 1
)

endlocal
