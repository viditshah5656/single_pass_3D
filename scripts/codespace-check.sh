#!/usr/bin/env bash
set -euo pipefail

cd "$(git rev-parse --show-toplevel)"
source /opt/venv/bin/activate 2>/dev/null || true

printf '\n== Python syntax ==\n'
python -m compileall -q app tests

printf '\n== Platform diagnostics ==\n'
python -m app.main doctor --json

printf '\n== Unit tests ==\n'
pytest -q

printf '\nCodespace checks completed.\n'
