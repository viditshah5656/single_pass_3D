#!/usr/bin/env bash
set -euo pipefail

cd "$(git rev-parse --show-toplevel)"

echo "== Python syntax =="
python -m compileall -q app tests

echo "== Unit/integrity tests =="
python -m pytest -q

echo "== Native backend =="
missing=0
for binary in InterfaceCOLMAP DensifyPointCloud ReconstructMesh TextureMesh; do
  if [[ -x ".local/bin/$binary" ]]; then
    ".local/bin/$binary" --help >/dev/null
    echo "OK  $binary"
  elif command -v "$binary" >/dev/null 2>&1; then
    "$binary" --help >/dev/null
    echo "OK  $binary (PATH)"
  else
    echo "MISSING  $binary"
    missing=1
  fi
done

echo "== Doctor =="
python -m app.main doctor --strict --json

if [[ "$missing" -ne 0 ]]; then
  echo "Full native reconstruction backend is incomplete." >&2
  exit 2
fi

echo
echo "AeroSynth full runtime validation passed."
