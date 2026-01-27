@echo off
setlocal
cd /d %~dp0
if not exist logs mkdir logs
python F001_app.py 1>>logs\F001_start.log 2>>&1
endlocal
