@echo off
setlocal EnableExtensions EnableDelayedExpansion
cd /d "%~dp0"

for %%V in (3.14 3.13 3.12 3.11) do (
    py -%%V -c "import sys" >nul 2>&1
    if not errorlevel 1 (
        py -%%V -m projects.bootstrap %*
        set "exit_code=!errorlevel!"
        goto finished
    )
)

python -c "import sys; raise SystemExit(sys.version_info < (3, 11))" >nul 2>&1
if not errorlevel 1 (
    python -m projects.bootstrap %*
    set "exit_code=!errorlevel!"
    goto finished
)

echo Python 3.11 oder neuer wurde nicht gefunden.
echo Python 3.11 or newer was not found.
set "exit_code=2"

:finished
if not "!exit_code!"=="0" pause
exit /b !exit_code!
