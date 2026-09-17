#!/usr/bin/env bash
set -euo pipefail

cd "$(git rev-parse --show-toplevel)"

# Be self-healing: the Dockerfile installs these in a fresh image, but we also
# verify/install them here so a reused Codespace cannot end up half-configured.
sudo apt-get update
sudo DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
  ffmpeg \
  build-essential \
  cmake \
  ninja-build \
  pkg-config \
  libgl1 \
  libegl1 \
  libglib2.0-0 \
  libgomp1 \
  libomp-dev \
  libboost-all-dev \
  libcgal-dev \
  libeigen3-dev \
  libopencv-dev \
  libnanoflann-dev

if [[ ! -x /opt/venv/bin/python ]]; then
  sudo rm -rf /opt/venv
  sudo python -m venv --system-site-packages /opt/venv
fi
sudo chown -R "$(id -u):$(id -g)" /opt/venv
source /opt/venv/bin/activate

python -m pip install --upgrade pip setuptools wheel
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

echo
echo 'AeroSynth Codespace ready.'
printf 'Python: '; python --version
printf 'Python path: '; command -v python
printf 'FFmpeg: '; command -v ffmpeg
printf 'Torch: '; python -c 'import torch; print(torch.__version__)'
printf 'Run: python -m app.main doctor --json\n'
printf 'Run: python -m app.main serve --host 0.0.0.0 --port 8000\n'
