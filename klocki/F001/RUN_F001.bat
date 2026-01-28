@echo off
setlocal
cd /d %~dp0
if not exist ..\F001_runtime mkdir ..\F001_runtime
python -B F001_panel.py
endlocal
