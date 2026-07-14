@echo off
REM Red Arc Ops Tool — start the local app and open it in the browser.
cd /d "%~dp0"
where py >nul 2>nul && (set PY=py) || (set PY=python)
%PY% -m pip install -r requirements.txt
start "" http://127.0.0.1:5000
%PY% -m app.server
