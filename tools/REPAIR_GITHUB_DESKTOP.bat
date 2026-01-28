@echo off
setlocal
set ROOT=%~dp0..
pushd "%ROOT%"
for /f %%i in ('powershell -NoProfile -Command "Get-Date -Format yyyyMMdd_HHmmss"') do set TS=%%i
set BACKUP_DIR=tools\_backup\%TS%
mkdir "%BACKUP_DIR%" >nul 2>&1

if exist klocki\F001\_runtime\state\portals.json (
  copy klocki\F001\_runtime\state\portals.json "%BACKUP_DIR%" >nul
)
if exist klocki\F001\_runtime\config\selectors.json (
  copy klocki\F001\_runtime\config\selectors.json "%BACKUP_DIR%" >nul
)

for /d /r %%D in (__pycache__) do (
  rmdir /s /q "%%D"
)

del /s /q *.pyc *.pyo 2>nul

echo Sprzatniete. Sprobuj Pull ponownie.
popd
endlocal
