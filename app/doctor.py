"""Cross-platform preflight and smoke diagnostics for AeroSynth 3D."""
from __future__ import annotations

import argparse
import importlib.util
import json
import os
import subprocess
import sys
from pathlib import Path

from app.platform import diagnostics, detect_host
from app.config import find_binary, find_glomap_binary, logger
from app.reconstruction.openmvs import find_openmvs_binary

REQUIRED_PYTHON = ("numpy", "cv2", "PIL", "open3d", "pycolmap", "fastapi", "pydantic")
OPTIONAL_PYTHON = ("torch", "torchvision", "ultralytics", "trimesh", "pygltflib", "laspy", "pyproj", "rasterio")
REQUIRED_OPENMVS = ("InterfaceCOLMAP", "DensifyPointCloud", "ReconstructMesh", "TextureMesh")


def _module_status(names: tuple[str, ...]) -> dict[str, bool]:
    return {name: importlib.util.find_spec(name) is not None for name in names}


def _probe_binary(path: str | None) -> dict[str, object]:
    if not path:
        return {"found": False, "path": None, "executable": False}
    try:
        result = subprocess.run([path, "--help"], capture_output=True, text=True, timeout=8, check=False)
        return {
            "found": True,
            "path": path,
            "executable": result.returncode == 0 or bool(result.stdout) or bool(result.stderr),
            "returncode": result.returncode,
        }
    except Exception as exc:
        return {"found": True, "path": path, "executable": False, "error": str(exc)}


def run_doctor(video: str | None = None, strict: bool = False) -> tuple[int, dict[str, object]]:
    host = detect_host()
    report = diagnostics()
    report["python_packages"] = {
        "required": _module_status(REQUIRED_PYTHON),
        "optional": _module_status(OPTIONAL_PYTHON),
    }
    report["native_backends"] = {
        "glomap": _probe_binary(find_glomap_binary()),
        "colmap": _probe_binary(find_binary("colmap")),
        "openmvs": {
            name: _probe_binary(find_openmvs_binary(name))
            for name in REQUIRED_OPENMVS
        },
    }

    if video:
        from app.video.extractor import VideoExtractor

        path = Path(video).expanduser().resolve()
        if not path.is_file():
            report["video"] = {"valid": False, "error": f"Video not found: {path}"}
        else:
            try:
                extractor = VideoExtractor()
                metadata = extractor.get_metadata(path)
                extractor.validate_capture_profile(metadata)
                report["video"] = {
                    "valid": True,
                    "path": str(path),
                    "fps": metadata.fps,
                    "width": metadata.width,
                    "height": metadata.height,
                    "frames": metadata.total_frames,
                    "duration_sec": metadata.duration_sec,
                }
            except Exception as exc:
                report["video"] = {"valid": False, "path": str(path), "error": str(exc)}

    required_ok = all(report["python_packages"]["required"].values())
    openmvs_ok = all(item["found"] and item["executable"] for item in report["native_backends"]["openmvs"].values())
    pycolmap_ok = bool(report["python_packages"]["required"].get("pycolmap"))
    video_ok = report.get("video", {}).get("valid", True)
    full_ready = required_ok and pycolmap_ok and openmvs_ok and video_ok

    report["summary"] = {
        "host": host.os,
        "machine": host.machine,
        "full_reconstruction_ready": full_ready,
        "sfm_ready": required_ok and pycolmap_ok and video_ok,
        "dense_mvs_ready": full_ready,
        "portable_cpu_path": required_ok and pycolmap_ok,
        "strict": strict,
    }

    if strict and not full_ready:
        logger.error("Doctor failed strict preflight: full reconstruction prerequisites are not ready.")
        return 2, report
    return 0, report


def main() -> int:
    parser = argparse.ArgumentParser(description="AeroSynth 3D cross-platform environment doctor")
    parser.add_argument("video", nargs="?", help="Optional drone video to validate in addition to the host")
    parser.add_argument("--json", action="store_true", help="Emit machine-readable JSON")
    parser.add_argument("--strict", action="store_true", help="Exit non-zero unless the full dense pipeline is ready")
    args = parser.parse_args()

    code, report = run_doctor(args.video, args.strict)
    if args.json:
        print(json.dumps(report, indent=2, sort_keys=True))
    else:
        summary = report["summary"]
        print(f"Host: {report['host']['os']} / {report['host']['machine']} / Python {report['host']['python']}")
        print(f"Full reconstruction ready: {'YES' if summary['full_reconstruction_ready'] else 'NO'}")
        print(f"Portable CPU path: {'YES' if summary['portable_cpu_path'] else 'NO'}")
        torch_info = report.get("torch", {})
        print(f"PyTorch: {torch_info.get('version', 'not installed')} | CUDA={torch_info.get('cuda_available', False)} | MPS={torch_info.get('mps_available', False)}")
        print("OpenMVS:")
        for name, item in report["native_backends"]["openmvs"].items():
            print(f"  {name:18} {'OK' if item['found'] and item['executable'] else 'MISSING'} {item.get('path') or ''}")
        print("Python required packages:")
        for name, ok in report["python_packages"]["required"].items():
            print(f"  {name:18} {'OK' if ok else 'MISSING'}")
        if "video" in report:
            print(f"Video: {'OK' if report['video']['valid'] else 'INVALID'}")
            if report['video']['valid']:
                print(f"  {report['video']['width']}x{report['video']['height']} @ {report['video']['fps']:.2f} FPS, {report['video']['duration_sec']:.2f}s")
            else:
                print(f"  {report['video']['error']}")
    return code


if __name__ == "__main__":
    raise SystemExit(main())
