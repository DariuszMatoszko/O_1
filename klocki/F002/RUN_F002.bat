@echo off
setlocal
cd /d %~dp0

REM Bootstrap log dla uruchomień z Launchera (VBS ukrywa konsolę).
if not exist "logs" mkdir "logs"

set LOGFILE=logs\F002_bootstrap.log
echo [%date% %time%] START >> "%LOGFILE%"

python -B F002_panel.py >> "%LOGFILE%" 2>&1
set RC=%ERRORLEVEL%

echo [%date% %time%] EXIT %RC% >> "%LOGFILE%"

if not "%RC%"=="0" (
  REM Jeśli coś padło zanim pokaże się okno – otwórz log automatycznie.
  start "" notepad "%LOGFILE%"
)

endlocal
