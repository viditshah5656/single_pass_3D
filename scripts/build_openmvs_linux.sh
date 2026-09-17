#!/usr/bin/env bash
set -euo pipefail

cd "$(git rev-parse --show-toplevel)"

OPENMVS_DIR="${OPENMVS_DIR:-third_party/openMVS}"
BUILD_DIR="${OPENMVS_BUILD_DIR:-${OPENMVS_DIR}/build}"
INSTALL_DIR="${OPENMVS_INSTALL_DIR:-$PWD/.local/openmvs}"
JOBS="${CMAKE_BUILD_PARALLEL_LEVEL:-$(nproc)}"

mkdir -p third_party .local/bin

if [[ ! -d "$OPENMVS_DIR/.git" ]]; then
  git clone --recurse-submodules https://github.com/cdcseacave/openMVS.git "$OPENMVS_DIR"
else
  git -C "$OPENMVS_DIR" submodule update --init --recursive
fi

cmake -S "$OPENMVS_DIR" -B "$BUILD_DIR" -GNinja \
  -DCMAKE_BUILD_TYPE=Release \
  -DCMAKE_INSTALL_PREFIX="$INSTALL_DIR" \
  -DOpenMVS_USE_CUDA=OFF

cmake --build "$BUILD_DIR" --parallel "$JOBS"
cmake --install "$BUILD_DIR"

for binary in InterfaceCOLMAP DensifyPointCloud ReconstructMesh TextureMesh; do
  candidate="$(find "$BUILD_DIR" "$INSTALL_DIR" -type f -name "$binary" -perm -111 -print -quit 2>/dev/null || true)"
  if [[ -n "$candidate" ]]; then
    ln -sf "$(realpath "$candidate")" ".local/bin/$binary"
    printf 'Linked %-22s %s\n' "$binary" "$candidate"
  else
    printf 'Missing required OpenMVS binary: %s\n' "$binary" >&2
    exit 1
  fi
done

printf '\nOpenMVS binaries:\n'
for binary in InterfaceCOLMAP DensifyPointCloud ReconstructMesh TextureMesh; do
  "$PWD/.local/bin/$binary" --help >/dev/null
  printf '  OK  %s\n' "$binary"
done
