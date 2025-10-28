@echo off
setlocal
set EXE=SenseisUpdater.exe
if exist "%~dp0dist\%EXE%" (
  set TARGET="%~dp0dist\%EXE%"
) else (
  set TARGET="%~dp0%EXE%"
)
powershell -NoProfile -ExecutionPolicy Bypass -Command ^
  "if (-not (Test-Path %TARGET%)) { Write-Host 'Missing %EXE% (build it first).'; exit 1 }; Start-Process -FilePath %TARGET% -Verb RunAs"
endlocal