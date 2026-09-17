"""Portable host and acceleration detection for AeroSynth 3D.

This module is stdlib-only so it can run before heavyweight CV/GPU packages.
It separates compute acceleration (CUDA/MPS/CPU) from the photogrammetry
backends (COLMAP/GLOMAP/OpenMVS), which keeps the pipeline portable across
Linux, macOS and Windows/WSL.
"""
from __future__ import annotations

import os
import platform
import shutil
import subprocess
import sys
from dataclasses import asdict, dataclass


@dataclass(frozen=True)
class HostInfo:
    os: str
    kernel: str
    architecture: str
    machine: str
    python: str
    is_wsl: bool
    is_rosetta: bool
    cpu_count: int


@dataclass(frozen=True)
class ComputeInfo:
    backend: str
    accelerator: str
    device_name: str
    available: bool
    reason: str


def _run_text(command: list[str]) -> str:
    try:
        result = subprocess.run(command, capture_output=True, text=True, timeout=3, check=False)
        return result.stdout.strip()
    except Exception:
        return ""


def detect_host() -> HostInfo:
    uname = platform.uname()
    machine = platform.machine().lower()
    kernel = uname.release
    is_wsl = "microsoft" in kernel.lower() or bool(os.environ.get("WSL_INTEROP"))
    is_rosetta = False
    if sys.platform == "darwin" and machine == "x86_64":
        is_rosetta = _run_text(["sysctl", "-in", "sysctl.proc_translated"]) == "1"

    if sys.platform.startswith("linux"):
        host_os = "linux"
    elif sys.platform == "darwin":
        host_os = "macos"
    elif os.name == "nt":
        host_os = "windows"
    else:
        host_os = sys.platform

    return HostInfo(
        os=host_os,
        kernel=kernel,
        architecture=platform.architecture()[0],
        machine=machine,
        python=platform.python_version(),
        is_wsl=is_wsl,
        is_rosetta=is_rosetta,
        cpu_count=os.cpu_count() or 1,
    )


def detect_compute() -> list[ComputeInfo]:
    """Return hardware candidates without importing PyTorch."""
    results: list[ComputeInfo] = []
    nvidia_smi = shutil.which("nvidia-smi")
    if nvidia_smi:
        name = _run_text([nvidia_smi, "--query-gpu=name", "--format=csv,noheader"]).splitlines()
        results.append(ComputeInfo("cuda", "NVIDIA CUDA", name[0].strip() if name else "NVIDIA GPU", True, "nvidia-smi detected"))
    else:
        results.append(ComputeInfo("cuda", "NVIDIA CUDA", "", False, "nvidia-smi not found"))

    host = detect_host()
    results.append(
        ComputeInfo(
            "mps",
            "Apple Metal / MPS",
            "Apple GPU" if host.os == "macos" else "",
            host.os == "macos",
            "macOS host detected; PyTorch MPS capability is probed separately" if host.os == "macos" else "not a macOS host",
        )
    )
    results.append(ComputeInfo("cpu", "CPU", platform.processor() or "Host CPU", True, "portable baseline"))
    return results


def probe_torch() -> dict[str, object]:
    """Probe the installed PyTorch build without making PyTorch mandatory."""
    try:
        import torch  # type: ignore
    except Exception as exc:
        return {"installed": False, "error": str(exc)}

    info: dict[str, object] = {
        "installed": True,
        "version": getattr(torch, "__version__", "unknown"),
        "cuda_built": bool(getattr(torch.backends.cuda, "is_built", lambda: False)()),
        "cuda_available": bool(torch.cuda.is_available()),
        "mps_built": bool(torch.backends.mps.is_built()) if hasattr(torch.backends, "mps") else False,
        "mps_available": bool(torch.backends.mps.is_available()) if hasattr(torch.backends, "mps") else False,
    }
    if info["cuda_available"]:
        try:
            info["cuda_name"] = torch.cuda.get_device_name(0)
            info["cuda_vram_gb"] = round(torch.cuda.get_device_properties(0).total_memory / (1024**3), 2)
        except Exception as exc:
            info["cuda_probe_error"] = str(exc)
    if info["mps_available"]:
        try:
            info["mps_name"] = torch.backends.mps.get_name()
        except Exception:
            info["mps_name"] = "Apple GPU"
    return info


def choose_torch_device(requested: str = "auto") -> str:
    """Choose CUDA -> MPS -> CPU automatically, or honor an explicit request."""
    probe = probe_torch()
    if requested == "cpu":
        return "cpu"
    if requested == "cuda":
        if not probe.get("cuda_available"):
            raise RuntimeError("CUDA was explicitly requested but is not available to PyTorch.")
        return "cuda"
    if requested == "mps":
        if not probe.get("mps_available"):
            raise RuntimeError("MPS was explicitly requested but is not available to PyTorch.")
        return "mps"
    if requested != "auto":
        raise ValueError("compute backend must be one of: auto, cuda, mps, cpu")
    if probe.get("cuda_available"):
        return "cuda"
    if probe.get("mps_available"):
        return "mps"
    return "cpu"


def diagnostics() -> dict[str, object]:
    host = detect_host()
    return {
        "host": asdict(host),
        "compute_candidates": [asdict(item) for item in detect_compute()],
        "torch": probe_torch(),
        "executables": {name: shutil.which(name) for name in (
            "python", "ffmpeg", "colmap", "glomap", "InterfaceCOLMAP",
            "DensifyPointCloud", "ReconstructMesh", "RefineMesh", "TextureMesh",
        )},
        "environment": {
            "CUDA_VISIBLE_DEVICES": os.environ.get("CUDA_VISIBLE_DEVICES"),
            "PYTORCH_ENABLE_MPS_FALLBACK": os.environ.get("PYTORCH_ENABLE_MPS_FALLBACK"),
        },
    }
