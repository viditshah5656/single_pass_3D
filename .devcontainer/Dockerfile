FROM mcr.microsoft.com/devcontainers/python:1-3.11-bookworm

USER root

RUN apt-get update \
    && DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
        ffmpeg \
        build-essential \
        cmake \
        ninja-build \
        pkg-config \
        libgl1 \
        libglib2.0-0 \
        libgomp1 \
        libomp-dev \
    && rm -rf /var/lib/apt/lists/*

RUN mkdir -p /opt/venv \
    && chown -R vscode:vscode /opt/venv

USER vscode
