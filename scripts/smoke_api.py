#!/usr/bin/env python3
"""Bounded local API smoke test for Codespaces and native development machines."""
from __future__ import annotations

import json
import sys
import urllib.error
import urllib.request

BASE = (sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8000").rstrip("/")


def get(path: str) -> object:
    with urllib.request.urlopen(BASE + path, timeout=8) as response:
        if response.status != 200:
            raise RuntimeError(f"{path}: HTTP {response.status}")
        return json.loads(response.read().decode("utf-8"))


health = get("/api/v1/health")
preflight = get("/api/v1/preflight")

assert isinstance(health, dict) and health.get("status") == "ok", health
assert isinstance(preflight, dict) and preflight.get("status") in {"ready", "incomplete"}, preflight
print("health: OK")
print("preflight:", preflight.get("status"))
print("device:", preflight.get("device"))
print("glomap:", preflight.get("glomap"))
print("colmap:", preflight.get("colmap"))
print("OpenMVS:", preflight.get("openmvs"))
