#!/usr/bin/env bash
set -euo pipefail

cd "$(git rev-parse --show-toplevel)"

VENV=/opt/venv
if [[ ! -x "$VENV/bin/python" ]]; then
  python -m venv --system-site-packages "$VENV"
fi

source "$VENV/bin/activate"
python -m pip install --upgrade pip setuptools wheel

# Codespaces are the portable Linux/CPU validation environment. Native CUDA and
# Apple MPS are validated on their respective machines.
python -m pip install --extra-index-url https://download.pytorch.org/whl/cpu \
  torch torchvision

python - <<'PY'
from pathlib import Path
requirements = Path('requirements.txt').read_text(encoding='utf-8').splitlines()
filtered = [
    line for line in requirements
    if line.strip() not in {'torch', 'torchvision'}
    and not line.strip().startswith('torch==')
    and not line.strip().startswith('torchvision==')
]
Path('/tmp/requirements-codespaces.txt').write_text('\n'.join(filtered) + '\n', encoding='utf-8')
PY

python -m pip install -r /tmp/requirements-codespaces.txt

mkdir -p data/input data/uploads data/output data/workspace data/job_state .local/bin

git config --local core.autocrlf input

printf '\nAeroSynth Codespace ready.\n'
printf 'Python: '; python --version
printf 'Torch: '; python -c 'import torch; print(torch.__version__)'
printf 'FFmpeg: '; ffmpeg -version | head -n 1
printf 'Interpreter: '; command -v python
printf '\nRun: python -m app.main doctor --json\n'
printf 'Run: python -m app.main serve --host 0.0.0.0 --port 8000\n'
