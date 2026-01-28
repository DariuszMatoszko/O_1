@echo off
setlocal
set ROOT=%~dp0..
pushd "%ROOT%"
echo UWAGA: Ten skrypt usunie lokalne, niezacommitowane zmiany kodu.
choice /m "Kontynuowac?" /c YN
if errorlevel 2 goto :END

git fetch --all

git reset --hard origin/main

git clean -fd

echo Repozytorium zresetowane.

:END
popd
endlocal
