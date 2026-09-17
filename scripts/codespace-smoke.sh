#!/usr/bin/env bash
set -euo pipefail

ROOT="$(git rev-parse --show-toplevel)"
cd "$ROOT"

PORT="${AEROSYNTH_SMOKE_PORT:-8000}"
LOG_FILE="${TMPDIR:-/tmp}/aerosynth-codespace-${PORT}.log"

cleanup() {
  if [[ -n "${SERVER_PID:-}" ]] && kill -0 "$SERVER_PID" 2>/dev/null; then
    kill "$SERVER_PID" 2>/dev/null || true
    wait "$SERVER_PID" 2>/dev/null || true
  fi
}
trap cleanup EXIT

echo "== Python compile check =="
python -m compileall -q app tests

echo "== Platform diagnostics =="
python -m app.main doctor --json | tee "${TMPDIR:-/tmp}/aerosynth-doctor.json" >/dev/null

echo "== Unit tests =="
python -m pytest -q tests/test_platform.py tests/test_honesty.py

echo "== Start local API =="
python -m app.main serve --host 0.0.0.0 --port "$PORT" >"$LOG_FILE" 2>&1 &
SERVER_PID=$!

for attempt in {1..30}; do
  if curl -fsS "http://127.0.0.1:${PORT}/api/v1/health" >/tmp/aerosynth-health.json 2>/dev/null; then
    break
  fi
  if ! kill -0 "$SERVER_PID" 2>/dev/null; then
    echo "Server exited before health check. Log:" >&2
    cat "$LOG_FILE" >&2 || true
    exit 1
  fi
  sleep 1
done

curl -fsS "http://127.0.0.1:${PORT}/api/v1/health" | python -m json.tool
curl -fsS "http://127.0.0.1:${PORT}/api/v1/preflight" | python -m json.tool >/tmp/aerosynth-preflight.json

python - <<'PY'
import json
from pathlib import Path
health = json.loads(Path('/tmp/aerosynth-health.json').read_text())
assert health.get('status') == 'ok', health
preflight = json.loads(Path('/tmp/aerosynth-preflight.json').read_text())
assert 'python_packages' in preflight
assert 'openmvs' in preflight
print('Smoke test passed: API health + preflight schema are live.')
PY

echo
echo "Codespace smoke test complete."
echo "Forwarded Control Room/API: port ${PORT}"
