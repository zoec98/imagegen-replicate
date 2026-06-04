#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."

host="127.0.0.1"
debug_args=()
secure_network=0
export FLASK_DEBUG=0

while [[ "$#" -gt 0 ]]; do
  case "$1" in
    --secure-network)
      host="0.0.0.0"
      secure_network=1
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

if [[ "$secure_network" -eq 1 ]] &&
  [[ -f .env ]] &&
  grep -Eqx "IMAGEGEN_FLASK_SECRET_KEY=(dev-secret-change-me)?" .env; then
  echo "Warning: .env contains insecure IMAGEGEN_FLASK_SECRET_KEY." >&2
  echo "The app setup will replace it with a random secret before startup." >&2
fi

exec uv run flask --app imagegen.app run "${debug_args[@]}" --host "$host" --port 5002
