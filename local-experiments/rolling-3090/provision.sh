#!/bin/bash
set -euo pipefail
export DEBIAN_FRONTEND=noninteractive
if ! command -v docker >/dev/null; then
  apt-get -o Acquire::Retries=2 -o Acquire::http::Timeout=25 update
  apt-get -o DPkg::Lock::Timeout=900 install -y --no-install-recommends docker.io ca-certificates curl gnupg python3-yaml
fi
systemctl start docker
if ! command -v nvidia-ctk >/dev/null; then
  if ! apt-cache show nvidia-container-toolkit 2>/dev/null | grep -q '^Package:'; then
    curl -fsSL --retry 2 --max-time 40 https://nvidia.github.io/libnvidia-container/gpgkey -o /root/rolling-3090/nvidia.key
    gpg --batch --yes --dearmor -o /usr/share/keyrings/nvidia-container-toolkit-keyring.gpg /root/rolling-3090/nvidia.key
    printf '%s\n' 'deb [signed-by=/usr/share/keyrings/nvidia-container-toolkit-keyring.gpg] https://nvidia.github.io/libnvidia-container/stable/deb/amd64 /' >/etc/apt/sources.list.d/nvidia-container-toolkit.list
    apt-get -o Acquire::Retries=2 -o Acquire::https::Timeout=25 update
  fi
  apt-get -o DPkg::Lock::Timeout=900 install -y --no-install-recommends nvidia-container-toolkit
fi
if ! docker info --format '{{json .Runtimes}}' | grep -q '"nvidia"'; then
  nvidia-ctk runtime configure --runtime=docker
  systemctl restart docker
fi
docker version --format '{{.Server.Version}}'
docker info --format '{{json .Runtimes}}'
