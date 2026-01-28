@echo off
setlocal
set ROOT=%~dp0..
set SESSIONS=%ROOT%\klocki\F001\_runtime\sessions
if exist "%SESSIONS%" (
  rmdir /s /q "%SESSIONS%"
  mkdir "%SESSIONS%"
)
echo Sesje wyczyszczone.
endlocal
