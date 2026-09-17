FROM mcr.microsoft.com/devcontainers/python:1-3.11-bookworm

USER root

# Codespaces base images can carry third-party APT sources for tools unrelated to
# this repository. Disable the Yarn source so an unavailable signing key cannot
# block installation of the OS libraries AeroSynth actually needs.
RUN rm -f /etc/apt/sources.list.d/yarn.list \
    /etc/apt/sources.list.d/yarnpkg.list \
    /etc/apt/sources.list.d/yarnpkg.list.save \
    /etc/apt/sources.list.d/yarn.list.save || true

RUN apt-get update \
    && DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
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
    && rm -rf /var/lib/apt/lists/*

RUN mkdir -p /opt/venv \
    && chown -R vscode:vscode /opt/venv

USER vscode
