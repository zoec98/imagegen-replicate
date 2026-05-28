@echo off
setlocal

cd /d "%~dp0\.."

set FLASK_DEBUG=1
uv run flask --app imagegen.app run --debug --host 0.0.0.0 --port 5002
