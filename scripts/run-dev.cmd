@echo off
setlocal

cd /d "%~dp0\.."

set HOST=127.0.0.1
set DEBUG_ARGS=
set SECURE_NETWORK=0
set FLASK_DEBUG=0

:parse_args
if "%~1"=="" goto run_flask
if "%~1"=="--secure-network" (
    set HOST=0.0.0.0
    set SECURE_NETWORK=1
    shift
    goto parse_args
)
if "%~1"=="--dev" (
    set DEBUG_ARGS=--debug
    set FLASK_DEBUG=1
    shift
    goto parse_args
)
echo Usage: scripts\run-dev.cmd [--secure-network] [--dev]
exit /b 2

:run_flask
if "%SECURE_NETWORK%"=="1" if exist ".env" (
    findstr /x /c:"IMAGEGEN_FLASK_SECRET_KEY=dev-secret-change-me" /c:"IMAGEGEN_FLASK_SECRET_KEY=" ".env" >nul
    if not errorlevel 1 (
        echo Warning: .env contains insecure IMAGEGEN_FLASK_SECRET_KEY.
        echo The app setup will replace it with a random secret before startup.
    )
)
uv run flask --app imagegen.app run %DEBUG_ARGS% --host %HOST% --port 5002
