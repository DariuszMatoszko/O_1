@echo off
setlocal
cd /d %~dp0
if not exist _runtime mkdir _runtime
python -B F001_panel.py
endlocal
