#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."

export FLASK_DEBUG=1
exec uv run flask --app imagegen.app run --debug --host 0.0.0.0 --port 5002
