# AeroSynth 3D in GitHub Codespaces

This repository has a reproducible GitHub Codespaces development environment. The Codespace is a **development and validation environment**, not a substitute for an M4/Apple Silicon or NVIDIA CUDA workstation.

GitHub creates the Codespace in a development container defined under `.devcontainer/`. The configuration installs the project's Python dependencies, a CPU-only PyTorch build, FFmpeg, C/C++ build tools, CMake/Ninja, and the folders used by the reconstruction runtime.

## 1. Create the Codespace

Open the repository:

```text
https://github.com/viditshah5656/single_pass_3D
```

Choose **Code → Codespaces → Create codespace on main**. GitHub will build the repository's `.devcontainer/devcontainer.json` environment.

The project configuration is documented by GitHub as the standard mechanism for customizing a Codespace environment. See: https://docs.github.com/en/codespaces/setting-up-your-project-for-codespaces/adding-a-dev-container-configuration

## 2. Wait for the first container build

The `post-create.sh` script will:

1. create `/opt/venv`,
2. install CPU-only PyTorch/TorchVision,
3. install the remaining `requirements.txt` dependencies,
4. install FFmpeg and native build dependencies,
5. create runtime directories,
6. print a ready message.

The first build can be substantial because this project contains computer-vision and geometry dependencies.

## 3. Verify the Python environment

```bash
source /opt/venv/bin/activate
python --version
python -c "import torch; print(torch.__version__); print('CUDA:', torch.cuda.is_available()); print('MPS:', hasattr(torch.backends, 'mps') and torch.backends.mps.is_available())"
```

Expected in Codespaces: a Linux CPU environment. CUDA and Apple MPS should not be expected here.

## 4. Run the repository doctor

Human-readable:

```bash
python -m app.main doctor
```

Machine-readable:

```bash
python -m app.main doctor --json
```

Strict mode:

```bash
python -m app.main doctor --strict
```

The doctor separates the Python environment, SfM readiness, dense OpenMVS readiness, and portable CPU status. A Codespace may be useful even when OpenMVS is not installed yet.

## 5. Run syntax and unit checks

```bash
python -m compileall -q app tests
pytest -q
```

Or run the bundled check:

```bash
bash scripts/codespace-check.sh
```

## 6. Start the real FastAPI control room

```bash
python -m app.main serve --host 0.0.0.0 --port 8000
```

Codespaces forwards port 8000. Open the forwarded **AeroSynth API + Control Room** URL.

The same server exposes:

```text
/
/docs
/api/v1/health
/api/v1/preflight
/api/v1/system-info
```

## 7. Smoke-test the server

Keep the server running and open another terminal:

```bash
python scripts/smoke_api.py
```

A successful smoke test confirms that the API responds, the preflight endpoint is reachable, and the runtime can report its available native tools.

## 8. Test the static GitHub Pages experience separately

Public static site:

```text
https://viditshah5656.github.io/single_pass_3D/
```

GitHub Pages hosts the browser UI. It does **not** run Python, PyTorch, COLMAP, or OpenMVS. The heavy reconstruction process still runs on a machine hosting the FastAPI backend.

When the page is hosted publicly, set the Control Room **API base** field to a reachable backend URL. When the page is served by the FastAPI application inside the Codespace, use the forwarded API URL or the same-origin `/api/v1` route.

## 9. Full OpenMVS build inside Codespaces (optional)

The repository deliberately does not compile OpenMVS during every Codespace creation because it is a large native dependency and would make every environment slow to bootstrap.

For a Linux CPU dense-reconstruction environment, run:

```bash
bash scripts/build_openmvs_linux.sh
```

This clones OpenMVS with submodules, configures a native Release build with CUDA disabled, installs it under `.local/openmvs`, and links the required tools into `.local/bin`.

Then rerun:

```bash
python -m app.main doctor --json
python scripts/smoke_api.py
```

OpenMVS itself documents dense point-cloud reconstruction, mesh reconstruction, refinement, and texturing as the final multi-view stereo part of the photogrammetry chain: https://github.com/cdcseacave/openMVS

## 10. Run an actual reconstruction smoke test

Do not start with a long 4K flight. Use a short representative clip first:

```bash
python -m app.main run ./sample-flight.mp4 \
  --mapper-backend pycolmap \
  --compute-backend cpu \
  --target-fps 2 \
  --max-frames 60 \
  --workspace-dir data/workspace/codespace-smoke \
  --output-dir data/output/codespace-smoke
```

Then inspect:

```bash
cat data/output/codespace-smoke/manifest.json
ls -lh data/output/codespace-smoke/
```

The runtime's artifact gate should reject a run whose required deliverables are missing or empty.

## 11. Codespace vs M4 vs NVIDIA

| Environment | Intended use | GPU path | Dense MVS |
|---|---|---|---|
| GitHub Codespace | Development, tests, API/UI integration | CPU PyTorch | Native OpenMVS CPU if built |
| MacBook M4 | Native production validation | Apple MPS for supported PyTorch stages | Native OpenMVS CPU/native |
| NVIDIA Linux/Windows | Production GPU validation | CUDA for supported PyTorch stages | Native OpenMVS; CUDA where its build supports it |

The distinction matters: the browser GPU, PyTorch MPS/CUDA, and OpenMVS native compute are separate execution layers.

## 12. Rebuilding the Codespace after config changes

When `.devcontainer/devcontainer.json` changes, use the VS Code command palette and select:

**Codespaces: Rebuild Container**

GitHub documents rebuilding the container as the way to apply updated dev-container configuration to an existing Codespace.

## 13. Daily development loop

```bash
# terminal 1
source /opt/venv/bin/activate
python -m app.main serve --host 0.0.0.0 --port 8000

# terminal 2
python -m compileall -q app tests
pytest -q
python scripts/smoke_api.py

# inspect after reconstruction
python -m app.main doctor --json
cat data/output/<job-id>/manifest.json
```

This gives a clean separation between code editing, API verification, preflight checks, and real reconstruction.
