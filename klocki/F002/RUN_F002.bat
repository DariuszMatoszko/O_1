@echo off
setlocal
cd /d %~dp0
if not exist ..\F002_runtime mkdir ..\F002_runtime
python -B F002_panel.py
endlocal
