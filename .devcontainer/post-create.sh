#!/usr/bin/env bash
set -euo pipefail

cd "$(git rev-parse --show-toplevel)"

python -m venv --system-site-packages /opt/venv
source /opt/venv/bin/activate
python -m pip install --upgrade pip setuptools wheel

# Codespaces are Linux/x86_64 CPU development machines. Keep PyTorch CPU-only here;
# CUDA and Apple MPS are validated on their respective native machines.
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

sudo apt-get update
sudo DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
  ffmpeg \
  build-essential \
  cmake \
  ninja-build \
  pkg-config \
  libgl1 \
  libglib2.0-0 \
  libgomp1 \
  libomp-dev

mkdir -p data/input data/uploads data/output data/workspace data/job_state .local/bin

git config --local core.autocrlf input

echo
printf 'AeroSynth Codespace ready.\n'
printf 'Python: '; python --version
printf 'Torch: '; python -c 'import torch; print(torch.__version__)'
printf 'Run: python -m app.main doctor --json\n'
printf 'Run: python -m app.main serve --host 0.0.0.0 --port 8000\n'
