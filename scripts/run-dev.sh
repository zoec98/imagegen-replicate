#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."

host="127.0.0.1"
debug_args=()
export FLASK_DEBUG=0

while [[ "$#" -gt 0 ]]; do
  case "$1" in
    --secure-network)
      host="0.0.0.0"
      ;;
    --dev)
      debug_args=(--debug)
      export FLASK_DEBUG=1
      ;;
    *)
      echo "Usage: scripts/run-dev.sh [--secure-network] [--dev]" >&2
      exit 2
      ;;
  esac
  shift
done

exec uv run flask --app imagegen.app run "${debug_args[@]}" --host "$host" --port 5002
