# Universal Platform Guide

AeroSynth 3D separates **compute acceleration** from **photogrammetry backends**.

- NVIDIA Linux/Windows systems can expose CUDA to PyTorch and supported native tools.
- Apple Silicon Macs use PyTorch MPS for supported ML stages; native OpenMVS remains a CPU/native C++ backend.
- CPU execution is always retained as the portable baseline.
- SfM/MVS capability is checked independently of whether CUDA or MPS exists.

## Apple Silicon M4 / macOS

Use a native arm64 Python environment. Avoid forcing x86_64/Rosetta unless a specific third-party binary requires it.

```bash
python3 --version
uname -m
sw_vers

python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt
```

The current PyCOLMAP documentation provides pre-built macOS wheels. COLMAP itself is also available through Homebrew, including Apple Silicon bottles.

```bash
brew install colmap
colmap -h
```

OpenMVS is not treated as a Python dependency. It must be available as native executables:

```text
InterfaceCOLMAP
DensifyPointCloud
ReconstructMesh
TextureMesh
```

Build/install OpenMVS natively for the Mac when those executables are not already available. Keep CUDA disabled on Apple Silicon; use the native CPU/OpenMP path.

## M4 acceleration check

```bash
python - <<'PY'
import torch
print("PyTorch:", torch.__version__)
print("MPS built:", hasattr(torch.backends, "mps") and torch.backends.mps.is_built())
print("MPS available:", hasattr(torch.backends, "mps") and torch.backends.mps.is_available())
if hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
    d = torch.device("mps")
    x = torch.ones((2048, 2048), device=d)
    print("MPS tensor test:", float((x * 2).mean().cpu()))
PY
```

Then run the project doctor:

```bash
python -m app.main doctor
python -m app.main doctor --json > doctor-m4.json
python -m app.main doctor --strict
```

`--strict` should only be expected to pass when all native dense-MVS prerequisites are present. A missing CUDA device on an M4 is normal; a missing OpenMVS native toolchain is the relevant dense-reconstruction blocker.

## NVIDIA CUDA system

```bash
python -m app.main doctor
python - <<'PY'
import torch
print("CUDA:", torch.cuda.is_available())
if torch.cuda.is_available():
    print(torch.cuda.get_device_name(0))
    print(round(torch.cuda.get_device_properties(0).total_memory / 1024**3, 2), "GB VRAM")
PY
```

For the full pipeline, verify that GLOMAP (optional), COLMAP, and the four OpenMVS executables are discoverable.

## CPU-only system

CPU is a supported baseline:

```bash
AEROSYNTH_COMPUTE_BACKEND=cpu python -m app.main doctor
AEROSYNTH_COMPUTE_BACKEND=cpu python -m app.main run /path/to/flight.mp4 --compute-backend cpu --mapper-backend pycolmap
```

CPU mode does not imply synthetic depth. Dense reconstruction still requires a real native MVS backend.

## Windows / WSL2

For Windows, use native Python for CPU/Windows-native toolchains, or WSL2 for a Linux/CUDA environment.

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
python -m app.main doctor
```

For WSL2, run the same Linux commands after activating the Linux virtual environment. The doctor reports WSL detection and native executable availability.

## Full reconstruction test

Do not start with a long 4K flight. First use a short, texture-rich, forward/nadir-overlap sample.

```bash
python -m app.main doctor path/to/sample.mp4
python -m app.main run path/to/sample.mp4 \
  --mapper-backend pycolmap \
  --compute-backend auto \
  --target-fps 2 \
  --max-frames 80 \
  --output-dir data/output/smoke
```

Then inspect:

```bash
cat data/output/smoke/manifest.json
curl http://127.0.0.1:8000/api/v1/available/<JOB_ID>
```

The run must fail when real prerequisites or declared output artifacts are missing. An attractive placeholder mesh is never considered a successful test.

## Performance tiers

For laptops, start with a short smoke run and conservative dense settings. Increase frame count, image resolution, and MVS workload only after SfM registers a healthy set of views and produces a strong sparse point cloud.

On an M4 Air, expect the AI preprocessing stages to use MPS when supported, while OpenMVS dense reconstruction and mesh processing use native CPU resources. The application therefore remains fully functional without pretending that Apple Metal accelerates an OpenMVS CUDA path.

## CI contract

Portable runtime tests run on:

- Ubuntu
- macOS
- Windows

CI intentionally tests importability, platform detection, CPU device selection, and Python compilation without requiring a developer's local GPU or OpenMVS build.
